from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# Engine - pool connection to the database
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Enable SQL query logging if debug mode is enabled
    pool_pre_ping=True,  # Enable connection pool pre-ping to check if connections are alive
    pool_size=5, # Set the maximum number of connections in the connection pool
    max_overflow=10, # Set the maximum number of connections that can be created beyond the pool size
    pool_recycle=3600, # Set the maximum lifetime of a connection in the pool (in seconds)
)

# Session factory - Create a session factory for creating new database sessions
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent automatic expiration of objects after commit
)

async def get_db():
    """
    Dependency function to get a database session.
    This function is used as a dependency in FastAPI routes to provide a database session for each request.
    It creates a new session, yields it for use in the route, and ensures that the session is closed after the request is completed.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session  # Yield the session for use in the route
        finally:
            await session.close()  # Ensure the session is closed after the request is completed