from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from core.config import settings
from core.utils.logger import logger

Base = declarative_base()

# Async database engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    """Create tables if they do not already exist."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified and synchronized.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise
