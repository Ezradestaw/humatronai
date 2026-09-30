import pytest
from core.models import User, SubscriptionTier
from core.services.student_service import StudentService
from core.services.subscription_service import SubscriptionService

@pytest.mark.asyncio
async def test_student_verification_flow(db_session):
    user = User()
    db_session.add(user)
    await db_session.commit()

    # Reject personal email
    success, msg, _ = await StudentService.request_student_verification(
        session=db_session,
        user_id=user.id,
        educational_email="student@gmail.com",
        institution_name="AAU"
    )
    assert success is False
    assert "accredited institution" in msg

    # Accept university email
    success, msg, rec = await StudentService.request_student_verification(
        session=db_session,
        user_id=user.id,
        educational_email="fikru@aau.edu.et",
        institution_name="Addis Ababa University"
    )
    assert success is True
    assert rec is not None
    assert rec.verification_code is not None

    # Invalid code
    ok, err_msg = await StudentService.confirm_student_code(db_session, user.id, "000000")
    assert ok is False

    # Valid code
    ok, succ_msg = await StudentService.confirm_student_code(db_session, user.id, rec.verification_code)
    assert ok is True
    assert "congratulations" in succ_msg.lower()

    # Verify status updated
    status = await StudentService.get_student_status(db_session, user.id)
    assert status["is_verified"] is True
    assert status["email"] == "fikru@aau.edu.et"

    # Confirm subscription is upgraded to Student
    dashboard = await SubscriptionService.get_usage_dashboard(db_session, user.id)
    assert dashboard["plan_tier"] == SubscriptionTier.STUDENT.value
