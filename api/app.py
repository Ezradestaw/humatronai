from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import init_db
from core.config import settings
from core.utils.logger import logger
from api.routes.health import router as health_router
from api.routes.auth_routes import router as auth_router
from api.routes.webhook import router as webhook_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Humatron API service...")
    await init_db()
    yield
    logger.info("Shutting down Humatron API service...")

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
