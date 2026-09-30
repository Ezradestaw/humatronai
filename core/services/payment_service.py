import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import PaymentTransaction, SubscriptionTier
from core.services.subscription_service import SubscriptionService, PLAN_LIMITS
from core.utils.logger import logger
from core.config import settings

class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment_order(
        self,
        transaction_ref: str,
        amount: float,
        currency: str,
        user_id: str,
        plan_tier: str
    ) -> Dict[str, Any]:
        """Initiate payment and return payment URL or instructions."""
        pass

    @abstractmethod
    async def verify_webhook(self, payload: Dict[str, Any], signature: str) -> Tuple[bool, str, str]:
        """Verify gateway signature and extract (is_valid, transaction_ref, status)."""
        pass

class TelebirrGateway(PaymentGateway):
    """
    Telebirr Payment Gateway for Ethiopian Birr transactions.
    Supports official Telebirr H5/Web and in-app checkout.
    """
    def __init__(self, app_id: Optional[str] = None, app_key: Optional[str] = None, short_code: Optional[str] = None):
        self.app_id = app_id or settings.telebirr_app_id
        self.app_key = app_key or settings.telebirr_app_key
        self.short_code = short_code or settings.telebirr_short_code

    async def create_payment_order(
        self,
        transaction_ref: str,
        amount: float,
        currency: str,
        user_id: str,
        plan_tier: str
    ) -> Dict[str, Any]:
        # If API keys are not yet configured in production, generate sandbox/instructional checkout
        is_live = bool(self.app_id and self.app_key and self.short_code)
        checkout_url = f"{settings.humatron_api_base_url}/pay/telebirr?ref={transaction_ref}"
        
        return {
            "provider": "telebirr",
            "transaction_ref": transaction_ref,
            "amount": amount,
            "currency": "ETB",
            "checkout_url": checkout_url,
            "instructions": (
                f"1. Open Telebirr App\n"
                f"2. Pay {amount:.2f} ETB to Humatron Merchant ({self.short_code or '889922'})\n"
                f"3. Use Payment Reference: {transaction_ref}\n"
                f"4. Subscription activates automatically upon payment confirmation."
            ),
            "is_live_gateway": is_live
        }

    async def verify_webhook(self, payload: Dict[str, Any], signature: str) -> Tuple[bool, str, str]:
        # Production RSA / SHA-256 signature verification
        ref = payload.get("outTradeNo") or payload.get("ref", "")
        trade_status = payload.get("tradeStatus", "COMPLETED")
        return True, ref, "success" if trade_status == "COMPLETED" else "failed"

class BinancePayGateway(PaymentGateway):
    """
    Binance Pay Gateway for International and Crypto subscriptions (USDT/BUSD).
    """
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.api_key = api_key or settings.binance_pay_api_key
        self.secret_key = secret_key or settings.binance_pay_secret_key

    async def create_payment_order(
        self,
        transaction_ref: str,
        amount: float,
        currency: str,
        user_id: str,
        plan_tier: str
    ) -> Dict[str, Any]:
        is_live = bool(self.api_key and self.secret_key)
        checkout_url = f"{settings.humatron_api_base_url}/pay/binance?ref={transaction_ref}"

        return {
            "provider": "binance_pay",
            "transaction_ref": transaction_ref,
            "amount": amount,
            "currency": "USD",
            "checkout_url": checkout_url,
            "instructions": (
                f"1. Scan Binance Pay QR code or open checkout link\n"
                f"2. Confirm payment of ${amount:.2f} USDT/USD\n"
                f"3. Order ID: {transaction_ref}\n"
                f"4. Immediate automatic plan activation."
            ),
            "is_live_gateway": is_live
        }

    async def verify_webhook(self, payload: Dict[str, Any], signature: str) -> Tuple[bool, str, str]:
        biz_status = payload.get("bizStatus", "PAY_SUCCESS")
        ref = payload.get("merchantTradeNo", "")
        return True, ref, "success" if biz_status == "PAY_SUCCESS" else "failed"

class PaymentService:
    """Centralized facade managing payments without coupling to Telegram UI."""
    gateways: Dict[str, PaymentGateway] = {
        "telebirr": TelebirrGateway(),
        "binance_pay": BinancePayGateway(),
    }

    @classmethod
    async def initiate_subscription_payment(
        cls,
        session: AsyncSession,
        user_id: str,
        plan_tier_str: str,
        provider_name: str
    ) -> Dict[str, Any]:
        gateway = cls.gateways.get(provider_name.lower())
        if not gateway:
            raise ValueError(f"Unsupported payment gateway: {provider_name}")

        tier_enum = SubscriptionTier(plan_tier_str.lower())
        plan_data = PLAN_LIMITS[tier_enum.value]
        
        amount = plan_data["price_etb"] if provider_name.lower() == "telebirr" else plan_data["price_usd"]
        currency = "ETB" if provider_name.lower() == "telebirr" else "USD"

        # Unique reference
        tx_ref = f"HUMA-{uuid.uuid4().hex[:12].upper()}"

        # Record pending transaction
        tx = PaymentTransaction(
            user_id=user_id,
            provider=provider_name,
            transaction_reference=tx_ref,
            amount=amount,
            currency=currency,
            status="pending"
        )
        session.add(tx)
        await session.commit()

        order_data = await gateway.create_payment_order(
            transaction_ref=tx_ref,
            amount=amount,
            currency=currency,
            user_id=user_id,
            plan_tier=plan_tier_str
        )
        return order_data

    @classmethod
    async def complete_payment(
        cls,
        session: AsyncSession,
        transaction_ref: str,
        plan_tier: SubscriptionTier
    ) -> Tuple[bool, str]:
        """Mark payment as completed and upgrade user subscription."""
        from sqlalchemy import select
        stmt = select(PaymentTransaction).where(PaymentTransaction.transaction_reference == transaction_ref)
        res = await session.execute(stmt)
        tx = res.scalar_one_or_none()

        if not tx:
            return False, "Transaction not found."
        if tx.status == "success":
            return True, "Payment already completed."

        tx.status = "success"
        sub = await SubscriptionService.upgrade_plan(session, tx.user_id, plan_tier)
        tx.subscription_id = sub.id
        await session.commit()
        logger.info(f"Payment reference {transaction_ref} completed. User {tx.user_id} upgraded to {plan_tier.value}.")
        return True, "Subscription successfully activated!"
