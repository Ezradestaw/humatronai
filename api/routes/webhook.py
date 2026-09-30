from fastapi import APIRouter, Request, Header, HTTPException
from aiogram.types import Update
from bot.main import create_bot_and_dispatcher
from core.config import settings
from core.utils.logger import logger

router = APIRouter(tags=["Telegram Webhook"])

# Cached instance for webhook handling
_bot = None
_dp = None

def get_bot_and_dp():
    global _bot, _dp
    if _bot is None or _dp is None:
        _bot, _dp = create_bot_and_dispatcher()
    return _bot, _dp

@router.post("/api/telegram-webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    """Production webhook endpoint for Telegram updates."""
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            logger.warning("Unauthorized webhook request rejected: Secret token mismatch.")
            raise HTTPException(status_code=403, detail="Forbidden: Invalid secret token.")

    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": get_bot_and_dp()[0]})
        bot, dp = get_bot_and_dp()
        await dp.feed_update(bot=bot, update=update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}
