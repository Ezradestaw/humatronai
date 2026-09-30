import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from core.utils.logger import logger

class RateLimitMiddleware(BaseMiddleware):
    """
    Leaky bucket rate limiter to prevent flooding and resource exhaustion.
    Limits each user to a max number of requests per window.
    """
    def __init__(self, rate_limit: float = 0.5):
        # Min seconds between requests from the same user
        self.rate_limit = rate_limit
        self.last_user_time: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            last_time = self.last_user_time.get(user_id, 0.0)
            if now - last_time < self.rate_limit:
                if isinstance(event, Message):
                    await event.answer("⚠️ Please slow down. Processing your previous request...")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Please wait a moment...", show_alert=False)
                return None
            self.last_user_time[user_id] = now

        return await handler(event, data)
