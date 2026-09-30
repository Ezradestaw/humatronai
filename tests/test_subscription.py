import pytest
from core.models import User, SubscriptionTier
from core.services.subscription_service import SubscriptionService, PLAN_LIMITS
from core.services.payment_service import PaymentService

@pytest.mark.asyncio
async def test_subscription_creation_and_quota(db_session):
    user = User()
    db_session.add(user)
    await db_session.commit()

    # Free subscription should be initialized
    sub = await SubscriptionService.get_or_create_user_subscription(db_session, user.id)
    assert sub.plan_tier == SubscriptionTier.FREE.value
    assert sub.max_monthly_files == 10

    # Quota check initially
    can_process, used, limit = await SubscriptionService.check_quota(db_session, user.id)
    assert can_process is True
    assert used == 0
    assert limit == 10

    # Simulate reaching limit
    for _ in range(10):
        await SubscriptionService.increment_usage(db_session, user.id)

    can_process, used, limit = await SubscriptionService.check_quota(db_session, user.id)
    assert can_process is False
    assert used == 10

@pytest.mark.asyncio
async def test_subscription_upgrade(db_session):
    user = User()
    db_session.add(user)
    await db_session.commit()

    # Upgrade to Student
    upgraded = await SubscriptionService.upgrade_plan(db_session, user.id, SubscriptionTier.STUDENT)
    assert upgraded.plan_tier == SubscriptionTier.STUDENT.value
    assert upgraded.max_monthly_files == 50

    # Check dashboard
    dashboard = await SubscriptionService.get_usage_dashboard(db_session, user.id)
    assert dashboard["plan_tier"] == SubscriptionTier.STUDENT.value
    assert dashboard["limit"] == 50

@pytest.mark.asyncio
async def test_payment_initiation_and_completion(db_session):
    user = User()
    db_session.add(user)
    await db_session.commit()

    # Telebirr order
    telebirr_order = await PaymentService.initiate_subscription_payment(
        session=db_session,
        user_id=user.id,
        plan_tier_str="student",
        provider_name="telebirr"
    )
    assert telebirr_order["provider"] == "telebirr"
    assert telebirr_order["currency"] == "ETB"
    assert telebirr_order["amount"] == 500.0
    assert "ref" in telebirr_order["checkout_url"]

    # Binance Pay order
    binance_order = await PaymentService.initiate_subscription_payment(
        session=db_session,
        user_id=user.id,
        plan_tier_str="pro",
        provider_name="binance_pay"
    )
    assert binance_order["provider"] == "binance_pay"
    assert binance_order["currency"] == "USD"
    assert binance_order["amount"] == 50.0

    # Complete payment
    success, msg = await PaymentService.complete_payment(
        session=db_session,
        transaction_ref=binance_order["transaction_ref"],
        plan_tier=SubscriptionTier.PRO
    )
    assert success is True
    
    # Confirm user plan is now PRO
    dashboard = await SubscriptionService.get_usage_dashboard(db_session, user.id)
    assert dashboard["plan_tier"] == SubscriptionTier.PRO.value
    assert dashboard["limit"] == 200
