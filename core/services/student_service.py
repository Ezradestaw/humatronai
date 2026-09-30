import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import StudentVerification, VerificationStatus, User, SubscriptionTier
from core.services.subscription_service import SubscriptionService
from core.utils.validators import is_academic_email
from core.utils.logger import logger
from core.config import settings

class StudentService:
    @staticmethod
    async def request_student_verification(
        session: AsyncSession,
        user_id: str,
        educational_email: str,
        institution_name: str
    ) -> Tuple[bool, str, Optional[StudentVerification]]:
        """
        Submit a student verification request.
        Validates the educational email domain (.edu, .edu.et, etc.).
        """
        clean_email = educational_email.strip().lower()
        if not is_academic_email(clean_email):
            return (
                False,
                "The email provided does not appear to be an accredited institution address (.edu, .edu.et, .ac.*). Please provide your official college/university email.",
                None
            )

        # Check existing verifications
        stmt = (
            select(StudentVerification)
            .where(StudentVerification.user_id == user_id)
            .order_by(StudentVerification.submitted_at.desc())
        )
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing and existing.status == VerificationStatus.VERIFIED.value:
            return True, "Your student status is already verified!", existing

        # Generate a 6-digit verification code or secure web verification token
        code = f"{secrets.randbelow(900000) + 100000}"

        verification = StudentVerification(
            user_id=user_id,
            educational_email=clean_email,
            institution_name=institution_name.strip() or "University / College",
            status=VerificationStatus.PENDING.value,
            verification_code=code
        )
        session.add(verification)
        await session.commit()
        await session.refresh(verification)

        logger.info(f"Created student verification request for User {user_id} ({clean_email})")
        return (
            True,
            f"Verification request registered for {clean_email}. Verification instructions have been issued.",
            verification
        )

    @staticmethod
    async def confirm_student_code(
        session: AsyncSession,
        user_id: str,
        code: str
    ) -> Tuple[bool, str]:
        """Verify the 6-digit code sent to student email and activate student tier."""
        stmt = (
            select(StudentVerification)
            .where(
                StudentVerification.user_id == user_id,
                StudentVerification.status == VerificationStatus.PENDING.value
            )
            .order_by(StudentVerification.submitted_at.desc())
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            return False, "No pending student verification found."

        if record.verification_code != code.strip():
            return False, "Invalid verification code. Please check your email and try again."

        record.status = VerificationStatus.VERIFIED.value
        record.verified_at = datetime.now(timezone.utc)

        # Update User flag
        stmt_user = select(User).where(User.id == user_id)
        user_res = await session.execute(stmt_user)
        user = user_res.scalar_one()
        user.is_student = True

        # Upgrade to student discount plan
        await SubscriptionService.upgrade_plan(session, user_id, SubscriptionTier.STUDENT)
        await session.commit()
        logger.info(f"Student verification successful for user {user_id}. Upgraded to Student tier.")
        return True, "Congratulations! Your student verification was successful. You now have access to the Student Discount Plan."

    @staticmethod
    async def get_student_status(session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Fetch current student verification status for user."""
        stmt = (
            select(StudentVerification)
            .where(StudentVerification.user_id == user_id)
            .order_by(StudentVerification.submitted_at.desc())
        )
        res = await session.execute(stmt)
        rec = res.scalar_one_or_none()

        if not rec:
            return {"status": "none", "is_verified": False}

        return {
            "status": rec.status,
            "is_verified": rec.status == VerificationStatus.VERIFIED.value,
            "email": rec.educational_email,
            "institution": rec.institution_name,
            "submitted_at": rec.submitted_at.strftime("%d %b %Y"),
        }
