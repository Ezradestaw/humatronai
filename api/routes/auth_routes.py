from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db_session
from core.services.account_service import AccountService
from core.utils.security import verify_signed_token

router = APIRouter(prefix="/api/auth", tags=["Authentication & Account Linking"])

class LinkTelegramRequest(BaseModel):
    token: str = Field(..., description="Short-lived signed linking token from bot")
    user_id: str = Field(..., description="Target Humatron Web User ID")

@router.get("/verify-token")
async def verify_linking_token(token: str):
    """Check if token is cryptographically valid and not expired."""
    is_valid, telegram_id, reason = verify_signed_token(token)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)
    return {
        "valid": True,
        "telegram_id": telegram_id,
        "message": "Token is active and ready for linking."
    }

@router.post("/link-telegram")
async def link_telegram_account(
    req: LinkTelegramRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Confirm account link between Humatron Web account and Telegram identity."""
    success, msg = await AccountService.redeem_linking_token(session, req.token, req.user_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {
        "success": True,
        "message": msg
    }
