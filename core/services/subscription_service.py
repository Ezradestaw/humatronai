from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import Subscription, UsageRecord, SubscriptionTier, SubscriptionStatus, User
from core.utils.logger import logger

PLAN_LIMITS = {
    SubscriptionTier.FREE.value: {"files": 10, "price_usd": 0.0, "price_etb": 0.0, "name": "Free"},
    SubscriptionTier.STUDENT.value: {"files": 50, "price_usd": 5.0, "price_etb": 500.0, "name": "Student Discount"},
    SubscriptionTier.PRO.value: {"files": 200, "price_usd": 50.0, "price_etb": 5000.0, "name": "Pro"},
}

class SubscriptionService:
    @staticmethod
    def get_current_month_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @staticmethod
    async def get_or_create_user_subscription(session: AsyncSession, user_id: str) -> Subscription:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE.value)
            .order_by(Subscription.created_at.desc())
        )
        res = await session.execute(stmt)
        sub = res.scalar_one_or_none()
        if not sub:
            sub = Subscription(
                user_id=user_id,
                plan_tier=SubscriptionTier.FREE.value,
                status=SubscriptionStatus.ACTIVE.value,
                max_monthly_files=PLAN_LIMITS[SubscriptionTier.FREE.value]["files"]
            )
            session.add(sub)
            await session.commit()
            await session.refresh(sub)
        return sub

    @staticmethod
    async def get_monthly_usage(session: AsyncSession, user_id: str) -> UsageRecord:
        month_key = SubscriptionService.get_current_month_key()
        stmt = select(UsageRecord).where(
            UsageRecord.user_id == user_id,
            UsageRecord.month_year == month_key
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            record = UsageRecord(user_id=user_id, month_year=month_key, files_processed=0)
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return record

    @staticmethod
    async def check_quota(session: AsyncSession, user_id: str) -> Tuple[bool, int, int]:
        """
        Check if user has remaining processing quota for the current month.
        Returns: (can_process, used_files, limit_files)
        """
        sub = await SubscriptionService.get_or_create_user_subscription(session, user_id)
        usage = await SubscriptionService.get_monthly_usage(session, user_id)

        limit = sub.max_monthly_files
        used = usage.files_processed
        can_process = used < limit
        return can_process, used, limit

    @staticmethod
    async def increment_usage(session: AsyncSession, user_id: str) -> int:
        """Increment files processed counter."""
        usage = await SubscriptionService.get_monthly_usage(session, user_id)
        usage.files_processed += 1
        usage.last_processed_at = datetime.now(timezone.utc)
        await session.commit()
        return usage.files_processed

    @staticmethod
    async def get_usage_dashboard(session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Get formatted usage details for Telegram UI."""
        sub = await SubscriptionService.get_or_create_user_subscription(session, user_id)
        usage = await SubscriptionService.get_monthly_usage(session, user_id)

        plan_info = PLAN_LIMITS.get(sub.plan_tier, PLAN_LIMITS[SubscriptionTier.FREE.value])
        remaining = max(0, sub.max_monthly_files - usage.files_processed)
        renewal = sub.renewal_date.strftime("%d %B %Y") if sub.renewal_date else "End of month"

        return {
            "plan_name": plan_info["name"],
            "plan_tier": sub.plan_tier,
            "used": usage.files_processed,
            "limit": sub.max_monthly_files,
            "remaining": remaining,
            "renewal": renewal,
            "price_usd": float(sub.price_usd),
            "price_etb": float(sub.price_etb),
        }

    @staticmethod
    async def upgrade_plan(
        session: AsyncSession,
        user_id: str,
        plan_tier: SubscriptionTier,
        duration_days: int = 30
    ) -> Subscription:
        """Upgrade or renew a user's subscription."""
        info = PLAN_LIMITS[plan_tier.value]
        now = datetime.now(timezone.utc)
        renewal = now + timedelta(days=duration_days)

        # Deactivate existing active subscriptions
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        )
        res = await session.execute(stmt)
        for existing in res.scalars():
            existing.status = SubscriptionStatus.EXPIRED.value

        new_sub = Subscription(
            user_id=user_id,
            plan_tier=plan_tier.value,
            status=SubscriptionStatus.ACTIVE.value,
            price_usd=info["price_usd"],
            price_etb=info["price_etb"],
            max_monthly_files=info["files"],
            start_date=now,
            renewal_date=renewal
        )
        session.add(new_sub)
        await session.commit()
        await session.refresh(new_sub)
        logger.info(f"User {user_id} upgraded to {plan_tier.value} plan successfully.")
        return new_sub
