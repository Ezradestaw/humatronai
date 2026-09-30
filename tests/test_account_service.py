import pytest
from core.models import User
from core.services.account_service import AccountService

@pytest.mark.asyncio
async def test_telegram_account_lifecycle(db_session):
    tg_id = 77889900

    # 1. Get or create account
    tg_account, user = await AccountService.get_or_create_telegram_account(
        session=db_session,
        telegram_id=tg_id,
        first_name="TestStudent",
        username="teststudent"
    )
    assert tg_account.telegram_id == tg_id
    assert tg_account.user_id == user.id

    # 2. Check profile
    profile = await AccountService.get_profile(db_session, tg_id)
    assert profile is not None
    assert profile["name"] == "TestStudent"
    assert profile["is_linked"] is False

    # 3. Generate linking token
    token = await AccountService.generate_linking_token(db_session, tg_id)
    assert token is not None

    # 4. Create Web User and redeem token
    web_user = User(email="teststudent@humatron.me", username="teststudent_web")
    db_session.add(web_user)
    await db_session.commit()

    ok, msg = await AccountService.redeem_linking_token(db_session, token, web_user.id)
    assert ok is True

    # Check updated profile
    profile_updated = await AccountService.get_profile(db_session, tg_id)
    assert profile_updated["is_linked"] is True
    assert profile_updated["humatron_email"] == "teststudent@humatron.me"

    # 5. Token reuse is blocked
    ok_repeat, msg_repeat = await AccountService.redeem_linking_token(db_session, token, web_user.id)
    assert ok_repeat is False

    # 6. Unlink
    ok_unlink, _ = await AccountService.unlink_telegram_account(db_session, tg_id)
    assert ok_unlink is True
    profile_unlinked = await AccountService.get_profile(db_session, tg_id)
    assert profile_unlinked["is_linked"] is False
