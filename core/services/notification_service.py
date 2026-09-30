from typing import Optional, List
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import TelegramAccount
from core.utils.logger import logger

class NotificationService:
    @staticmethod
    async def send_user_notification(
        bot: Bot,
        session: AsyncSession,
        telegram_id: int,
        message: str,
        parse_mode: str = "HTML",
        is_essential: bool = False
    ) -> bool:
        """
        Send a notification to a specific Telegram user.
        Respects notifications_enabled unless marked is_essential (e.g. security alerts).
        """
        try:
            stmt = select(TelegramAccount).where(TelegramAccount.telegram_id == telegram_id)
            res = await session.execute(stmt)
            account = res.scalar_one_or_none()

            if account and not account.notifications_enabled and not is_essential:
                logger.info(f"Notification suppressed for user {telegram_id} (user disabled non-essential alerts).")
                return False

            await bot.send_message(chat_id=telegram_id, text=message, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.warning(f"Failed to send notification to Telegram user {telegram_id}: {e}")
            return False

    @staticmethod
    async def broadcast_announcement(
        bot: Bot,
        session: AsyncSession,
        announcement_text: str
    ) -> int:
        """Broadcast message to all active users with notifications enabled."""
        stmt = select(TelegramAccount).where(
            TelegramAccount.is_active == True,
            TelegramAccount.notifications_enabled == True
        )
        res = await session.execute(stmt)
        accounts = res.scalars().all()

        success_count = 0
        formatted = f"📢 <b>Humatron Announcement</b>\n\n{announcement_text}"

        for acc in accounts:
            try:
                await bot.send_message(chat_id=acc.telegram_id, text=formatted, parse_mode="HTML")
                success_count += 1
            except Exception as e:
                logger.debug(f"Broadcast failed for {acc.telegram_id}: {e}")

        logger.info(f"Broadcast completed. Delivered to {success_count}/{len(accounts)} users.")
        return success_count
