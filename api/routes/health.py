from fastapi import APIRouter
from sqlalchemy import text
from core.database import async_session

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    db_status = "disconnected"
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "humatron-bot-api",
        "database": db_status
    }
