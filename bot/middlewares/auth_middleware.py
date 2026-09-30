from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from core.database import async_session
from core.services.account_service import AccountService
from core.utils.logger import logger

class AuthMiddleware(BaseMiddleware):
    """
    Middleware that manages the database session lifecycle per event,
    resolves the user's TelegramAccount and linked User, and passes them to handlers.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        if not from_user:
            return await handler(event, data)

        async with async_session() as session:
            try:
                tg_account, user = await AccountService.get_or_create_telegram_account(
                    session=session,
                    telegram_id=from_user.id,
                    first_name=from_user.first_name,
                    last_name=from_user.last_name,
                    username=from_user.username,
                    language_code=from_user.language_code or "en"
                )
                data["session"] = session
                data["tg_account"] = tg_account
                data["user"] = user

                return await handler(event, data)
            except Exception as e:
                logger.error(f"Error in AuthMiddleware for user {from_user.id}: {e}", exc_info=True)
                if isinstance(event, Message):
                    await event.answer("Something went wrong while processing your request. Please try again.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Something went wrong. Please try again.", show_alert=True)
                return None
