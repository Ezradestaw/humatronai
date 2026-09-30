from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from core.models import User, TelegramAccount, AccountLinkingToken, Subscription, SubscriptionTier
from core.utils.security import create_signed_token, verify_signed_token, generate_random_token
from core.utils.logger import logger
from core.config import settings

class AccountService:
    @staticmethod
    async def get_or_create_telegram_account(
        session: AsyncSession,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: str = "en"
    ) -> Tuple[TelegramAccount, User]:
        """
        Retrieve existing TelegramAccount or create one.
        If no associated User exists, an unlinked shadow User account is created automatically.
        """
        stmt = (
            select(TelegramAccount)
            .options(selectinload(TelegramAccount.user))
            .where(TelegramAccount.telegram_id == telegram_id)
        )
        res = await session.execute(stmt)
        tg_account = res.scalar_one_or_none()

        if tg_account:
            # Update activity timestamp and metadata
            tg_account.first_name = first_name
            tg_account.last_name = last_name
            tg_account.username = username
            tg_account.last_active_at = datetime.now(timezone.utc)
            if not tg_account.user:
                # Ensure a linked user exists
                user = User()
                session.add(user)
                await session.flush()
                tg_account.user_id = user.id
                tg_account.user = user
                # Grant free subscription
                sub = Subscription(user_id=user.id, plan_tier=SubscriptionTier.FREE.value)
                session.add(sub)
            await session.commit()
            return tg_account, tg_account.user

        # Create new user and telegram account
        user = User()
        session.add(user)
        await session.flush()

        # Free tier subscription for every new user
        sub = Subscription(user_id=user.id, plan_tier=SubscriptionTier.FREE.value)
        session.add(sub)

        # Check if telegram_id is an admin
        if telegram_id in settings.admin_telegram_ids:
            user.is_admin = True

        tg_account = TelegramAccount(
            telegram_id=telegram_id,
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
            last_active_at=datetime.now(timezone.utc)
        )
        session.add(tg_account)
        await session.commit()
        await session.refresh(tg_account)
        return tg_account, user

    @staticmethod
    async def generate_linking_token(session: AsyncSession, telegram_id: int) -> str:
        """
        Generate a secure, short-lived (10-minute) one-time token for linking to Humatron Web account.
        """
        signed_token = create_signed_token(telegram_id=telegram_id, expires_in_seconds=600)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        token_record = AccountLinkingToken(
            telegram_id=telegram_id,
            token=signed_token,
            expires_at=expires_at,
            is_used=False
        )
        session.add(token_record)
        await session.commit()
        logger.info(f"Generated account linking token for Telegram user {telegram_id}")
        return signed_token

    @staticmethod
    async def redeem_linking_token(session: AsyncSession, token_str: str, web_user_id: str) -> Tuple[bool, str]:
        """
        Verify and redeem a linking token on the Humatron web platform to attach a Telegram identity.
        """
        is_valid, telegram_id, reason = verify_signed_token(token_str)
        if not is_valid:
            return False, reason

        # Query token record
        stmt = select(AccountLinkingToken).where(
            AccountLinkingToken.token == token_str,
            AccountLinkingToken.is_used == False
        )
        res = await session.execute(stmt)
        token_record = res.scalar_one_or_none()

        if not token_record:
            return False, "Token has already been used or does not exist."

        # Fetch web user
        stmt_user = select(User).where(User.id == web_user_id)
        res_user = await session.execute(stmt_user)
        web_user = res_user.scalar_one_or_none()
        if not web_user:
            return False, "Target Humatron web account not found."

        # Fetch telegram account
        stmt_tg = select(TelegramAccount).where(TelegramAccount.telegram_id == telegram_id)
        res_tg = await session.execute(stmt_tg)
        tg_account = res_tg.scalar_one_or_none()
        if not tg_account:
            return False, "Telegram account record not found."

        # Link account
        old_user_id = tg_account.user_id
        tg_account.user_id = web_user.id
        tg_account.user = web_user
        token_record.is_used = True

        # If old shadow user had subscriptions or verifications, migrate or cleanup if unlinked
        await session.commit()
        await session.refresh(tg_account)
        logger.info(f"Successfully linked Telegram account {telegram_id} to Humatron User {web_user_id}")
        return True, "Account successfully linked!"

    @staticmethod
    async def unlink_telegram_account(session: AsyncSession, telegram_id: int) -> Tuple[bool, str]:
        """
        Unlink Telegram identity from the registered Humatron account.
        """
        stmt = select(TelegramAccount).where(TelegramAccount.telegram_id == telegram_id)
        res = await session.execute(stmt)
        tg_account = res.scalar_one_or_none()

        if not tg_account:
            return False, "Telegram account not found."

        # Create new standalone shadow user for telegram operations
        new_user = User()
        session.add(new_user)
        await session.flush()

        sub = Subscription(user_id=new_user.id, plan_tier=SubscriptionTier.FREE.value)
        session.add(sub)

        tg_account.user_id = new_user.id
        tg_account.user = new_user
        await session.commit()
        await session.refresh(tg_account)
        logger.info(f"Unlinked Telegram account {telegram_id} from Humatron web account.")
        return True, "Telegram account unlinked successfully."

    @staticmethod
    async def get_profile(session: AsyncSession, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve user profile summary for the Telegram UI.
        """
        stmt = (
            select(TelegramAccount)
            .options(
                selectinload(TelegramAccount.user).selectinload(User.subscriptions),
                selectinload(TelegramAccount.user).selectinload(User.student_verifications)
            )
            .where(TelegramAccount.telegram_id == telegram_id)
        )
        res = await session.execute(stmt)
        tg_account = res.scalar_one_or_none()
        if not tg_account:
            return None

        user = tg_account.user
        active_sub = None
        if user and user.subscriptions:
            for s in user.subscriptions:
                if s.status == "active":
                    active_sub = s
                    break

        student_status = "Not Verified"
        if user and user.is_student:
            student_status = "Verified Student 🎓"
        elif user and user.student_verifications:
            latest = sorted(user.student_verifications, key=lambda v: v.submitted_at, reverse=True)[0]
            student_status = f"Verification {latest.status.capitalize()}"

        is_linked = bool(user and (user.email or user.username))

        return {
            "telegram_id": tg_account.telegram_id,
            "name": f"{tg_account.first_name} {tg_account.last_name or ''}".strip(),
            "username": tg_account.username,
            "is_linked": is_linked,
            "humatron_email": user.email if is_linked else "Unlinked (Telegram Only)",
            "humatron_username": user.username if is_linked else None,
            "student_status": student_status,
            "is_student": user.is_student if user else False,
            "plan_tier": active_sub.plan_tier.capitalize() if active_sub else "Free",
            "notifications_enabled": tg_account.notifications_enabled,
            "is_admin": user.is_admin if user else False,
            "created_at": tg_account.created_at.strftime("%d %B %Y")
        }
