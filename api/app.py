import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import init_db
from core.config import settings
from core.utils.logger import logger
from api.routes.health import router as health_router
from api.routes.auth_routes import router as auth_router
from api.routes.webhook import router as webhook_router

_bot_task = None
_active_bot = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task, _active_bot
    logger.info("Starting Humatron API service...")
    await init_db()

    # When not in webhook mode, run bot polling inside the web service for seamless free-tier hosting on Render
    if not settings.use_webhook:
        from bot.main import create_bot_and_dispatcher, setup_bot_commands
        try:
            logger.info("Initializing Telegram bot within web service...")
            bot, dp = create_bot_and_dispatcher()
            _active_bot = bot
            await setup_bot_commands(bot)
            await bot.delete_webhook(drop_pending_updates=True)
            _bot_task = asyncio.create_task(
                dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            )
            logger.info("Humatron Bot background polling active.")
        except Exception as e:
            logger.warning(f"Could not start bot polling in lifespan: {e}")

    yield

    logger.info("Shutting down Humatron service...")
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
    if _active_bot:
        await _active_bot.session.close()

app = FastAPI(
    title="Humatron Companion Service API",
    description="Official companion service and backend for Humatron Telegram Bot and Web Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for humatron.me
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.humatron_api_base_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host=settings.host, port=settings.port, reload=True)
