import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings
from core.utils.logger import logger

Base = declarative_base()

def create_engine_for_url(db_url: str):
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args
    )

# Primary Async database engine
engine = create_engine_for_url(settings.async_database_url)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db(max_retries: int = 3):
    """
    Create tables if they do not exist.
    If PostgreSQL fails to connect (e.g. DATABASE_URL not yet configured on Render),
    retries, and gracefully falls back to SQLite to prevent crashing the web service.
    """
    global engine, async_session
    current_url = settings.async_database_url

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to database (attempt {attempt}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema verified and synchronized.")
            return
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if attempt < max_retries and "sqlite" not in current_url:
                await asyncio.sleep(2)
            else:
                # If on Render or cloud and PostgreSQL is unreachable, fall back to SQLite
                fallback_url = "sqlite+aiosqlite:///humatron.db"
                logger.warning(
                    f"⚠️ PostgreSQL connection failed. Falling back to local SQLite ('{fallback_url}') "
                    "so the service and Telegram bot can boot safely without crashing.\n"
                    "👉 To use PostgreSQL on Render: Create a PostgreSQL database on Render and set "
                    "the DATABASE_URL environment variable in your Render dashboard."
                )
                try:
                    engine = create_engine_for_url(fallback_url)
                    async_session = async_sessionmaker(
                        bind=engine,
                        class_=AsyncSession,
                        expire_on_commit=False
                    )
                    async with engine.begin() as conn:
                        await conn.run_sync(Base.metadata.create_all)
                    logger.info("SQLite fallback database initialized successfully.")
                    return
                except Exception as fallback_err:
                    logger.error(f"Fallback database initialization error: {fallback_err}")
                    return
