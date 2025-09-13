from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session
