import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from core.config import settings
from core.database import init_db
from core.utils.logger import logger
from bot.middlewares import RateLimitMiddleware, AuthMiddleware
from bot.handlers import get_main_router

# BotFather official commands
BOT_COMMANDS = [
    BotCommand(command="start", description="Open Humatron dashboard & menu"),
    BotCommand(command="account", description="View profile & link Humatron account"),
    BotCommand(command="pdf", description="Access student PDF tools"),
    BotCommand(command="usage", description="Check monthly quota & remaining usage"),
    BotCommand(command="subscription", description="View plans, upgrade & payments"),
    BotCommand(command="student", description="Student discount verification"),
    BotCommand(command="help", description="Frequently asked questions & support"),
    BotCommand(command="settings", description="Manage notifications & preferences"),
    BotCommand(command="admin", description="Administrator control panel"),
]

async def setup_bot_commands(bot: Bot):
    """Register official commands in Telegram Bot menu."""
    try:
        await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
        logger.info("Bot commands successfully registered with Telegram.")
    except Exception as e:
        logger.warning(f"Could not register bot commands: {e}")

def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    session = None
    if settings.telegram_proxy:
        from aiogram.client.session.aiohttp import AiohttpSession
        logger.info(f"Using configured proxy for Telegram connection.")
        session = AiohttpSession(proxy=settings.telegram_proxy)

    bot = Bot(
        token=settings.telegram_bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register Middlewares
    dp.message.middleware(RateLimitMiddleware(rate_limit=0.4))
    dp.callback_query.middleware(RateLimitMiddleware(rate_limit=0.4))
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Include Main Router
    dp.include_router(get_main_router())

    return bot, dp

async def run_polling():
    """Development entrypoint using long polling."""
    logger.info("Initializing Humatron database schema...")
    await init_db()

    logger.info("Starting Humatron Telegram Bot in long-polling development mode...")
    bot, dp = create_bot_and_dispatcher()

    await setup_bot_commands(bot)
    try:
        # Delete any existing webhook to enable clean polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_polling())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Humatron Bot stopped by user.")
