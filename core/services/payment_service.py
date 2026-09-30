import uuid
import os
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import PaymentTransaction, SubscriptionTier
from core.services.subscription_service import SubscriptionService, PLAN_LIMITS
from core.utils.logger import logger
from core.config import settings

BINANCE_RECIPIENT_NAME = "Burton Knick rZXe"
BINANCE_QR_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bot", "assets", "binance_qr.png")

class PaymentService:
    """
    PaymentService managing Binance Pay manual approval workflows.
    Users pay via Binance App scanning the merchant QR code, submit TxID/screenshot proof,
    and administrators review and approve in Telegram.
    """

    @classmethod
    async def initiate_subscription_payment(
        cls,
        session: AsyncSession,
        user_id: str,
        plan_tier_str: str,
        provider_name: str = "binance_pay"
    ) -> Dict[str, Any]:
        tier_enum = SubscriptionTier(plan_tier_str.lower())
        plan_data = PLAN_LIMITS[tier_enum.value]
        
        amount = plan_data["price_usd"]
        currency = "USDT"

        # Unique reference code for tracking
        tx_ref = f"HUMA-{uuid.uuid4().hex[:10].upper()}"

        # Record initial pending transaction
        tx = PaymentTransaction(
            user_id=user_id,
            provider="binance_pay",
            transaction_reference=tx_ref,
            amount=amount,
            currency=currency,
            status="pending"
        )
        session.add(tx)
        await session.commit()

        instructions = (
            f"1. Open your <b>Binance App</b> and tap the <b>QR Scanner</b>\n"
            f"2. Scan the Binance QR code displayed above\n"
            f"   • Recipient: <code>{BINANCE_RECIPIENT_NAME}</code>\n"
            f"3. Send exactly <b>${amount:.2f} USDT</b>\n"
            f"4. Enter Payment Reference in remark/note: <code>{tx_ref}</code>\n"
            f"5. After paying, tap <b>📤 Submit Payment Proof</b> below and send your Transaction ID (TxID) or screenshot."
        )

        return {
            "provider": "binance_pay",
            "transaction_ref": tx_ref,
            "amount": amount,
            "currency": currency,
            "recipient_name": BINANCE_RECIPIENT_NAME,
            "qr_image_path": BINANCE_QR_PATH,
            "plan_tier": tier_enum.value,
            "instructions": instructions
        }

    @classmethod
    async def submit_payment_proof(
        cls,
        session: AsyncSession,
        transaction_ref: str,
        proof_text: Optional[str] = None,
        proof_image_file_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[PaymentTransaction]]:
        """Store user proof and transition status to pending_approval."""
        stmt = select(PaymentTransaction).where(PaymentTransaction.transaction_reference == transaction_ref)
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            return False, "Transaction reference not found.", None

        tx.status = "pending_approval"
        tx.proof_details = proof_text
        tx.proof_image_file_id = proof_image_file_id
        await session.commit()
        await session.refresh(tx)

        logger.info(f"Payment proof submitted for {transaction_ref} by user {tx.user_id}")
        return True, "Payment proof submitted successfully.", tx

    @classmethod
    async def approve_manual_payment(
        cls,
        session: AsyncSession,
        transaction_ref: str,
        plan_tier: Optional[SubscriptionTier] = None
    ) -> Tuple[bool, str, Optional[PaymentTransaction]]:
        """Admin approves payment: upgrades user subscription and marks success."""
        stmt = select(PaymentTransaction).where(PaymentTransaction.transaction_reference == transaction_ref)
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            return False, "Transaction not found.", None
        if tx.status == "success":
            return True, "Payment was already approved.", tx

        # Determine plan tier from amount if not explicitly passed
        if not plan_tier:
            if float(tx.amount) >= 40.0:
                plan_tier = SubscriptionTier.PRO
            else:
                plan_tier = SubscriptionTier.STUDENT

        tx.status = "success"
        sub = await SubscriptionService.upgrade_plan(session, tx.user_id, plan_tier)
        tx.subscription_id = sub.id
        await session.commit()
        await session.refresh(tx)

        logger.info(f"Payment {transaction_ref} manually approved! User {tx.user_id} upgraded to {plan_tier.value}.")
        return True, f"Payment approved. User upgraded to {plan_tier.value.capitalize()} plan.", tx

    @classmethod
    async def reject_manual_payment(
        cls,
        session: AsyncSession,
        transaction_ref: str,
        reason: str = "Invalid proof or payment not found"
    ) -> Tuple[bool, str, Optional[PaymentTransaction]]:
        """Admin rejects payment."""
        stmt = select(PaymentTransaction).where(PaymentTransaction.transaction_reference == transaction_ref)
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            return False, "Transaction not found.", None

        tx.status = "rejected"
        tx.proof_details = f"{tx.proof_details or ''} [Rejected: {reason}]"
        await session.commit()
        await session.refresh(tx)

        logger.info(f"Payment {transaction_ref} rejected by admin. Reason: {reason}")
        return True, f"Payment rejected: {reason}", tx
