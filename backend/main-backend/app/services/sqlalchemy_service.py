from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.database_models import Base
import logging

logger = logging.getLogger(__name__)

# Async engine for PostgreSQL
async_engine = None
async_session_factory = None


async def init_database():
    """Initialize database connection and create tables."""
    global async_engine, async_session_factory
    
    try:
        # Convert synchronous URL to async URL
        database_url = settings.database_url
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        
        logger.info(f"Connecting to database: {database_url}")
        
        # Create async engine
        async_engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        
        # Create async session factory
        async_session_factory = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Database connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def get_session() -> AsyncSession:
    """Get database session."""
    if not async_session_factory:
        await init_database()
    
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database():
    """Close database connections."""
    global async_engine
    
    if async_engine:
        await async_engine.dispose()
        logger.info("Database connections closed") 