from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from database.models import Base
from config import config
import logging

logger = logging.getLogger(__name__)

# Initialize engine only if DATABASE_URL is provided
if config.database_url:
    engine = create_async_engine(
        config.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "timeout": 10,
            "statement_cache_size": 0,
        },
    )
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
else:
    engine = None
    AsyncSessionLocal = None
    logger.warning("DATABASE_URL not set! Database features disabled.")


async def init_db():
    if engine is None:
        logger.warning("Database not initialized - no DATABASE_URL")
        return
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Ma'lumotlar bazasi tayyorlandi!")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise