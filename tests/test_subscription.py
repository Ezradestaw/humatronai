import pytest
from core.models import User, SubscriptionTier
from core.services.subscription_service import SubscriptionService, PLAN_LIMITS
from core.services.payment_service import PaymentService, BINANCE_RECIPIENT_NAME

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
async def test_binance_manual_payment_flow(db_session):
    user = User()
    db_session.add(user)
    await db_session.commit()

    # 1. Initiate Binance payment order
    order = await PaymentService.initiate_subscription_payment(
        session=db_session,
        user_id=user.id,
        plan_tier_str="pro",
        provider_name="binance_pay"
    )
    assert order["provider"] == "binance_pay"
    assert order["currency"] == "USDT"
    assert order["amount"] == 50.0
    assert order["recipient_name"] == BINANCE_RECIPIENT_NAME
    assert "HUMA-" in order["transaction_ref"]

    tx_ref = order["transaction_ref"]

    # 2. User submits payment proof (TxID)
    ok_proof, msg_proof, tx = await PaymentService.submit_payment_proof(
        session=db_session,
        transaction_ref=tx_ref,
        proof_text="Binance TxID: 88472910394812"
    )
    assert ok_proof is True
    assert tx.status == "pending_approval"
    assert "88472910394812" in tx.proof_details

    # 3. Admin approves payment
    ok_approve, msg_approve, tx_app = await PaymentService.approve_manual_payment(
        session=db_session,
        transaction_ref=tx_ref,
        plan_tier=SubscriptionTier.PRO
    )
    assert ok_approve is True
    assert tx_app.status == "success"

    # 4. Confirm user plan is now PRO
    dashboard = await SubscriptionService.get_usage_dashboard(db_session, user.id)
    assert dashboard["plan_tier"] == SubscriptionTier.PRO.value
    assert dashboard["limit"] == 200
