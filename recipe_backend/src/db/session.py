from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _normalize_async_database_url(database_url: str) -> str:
    """
    Normalize Postgres URL to an async driver URL.

    Accepts either:
      - postgresql://...
      - postgresql+asyncpg://...

    Returns:
      An async-compatible SQLAlchemy URL.
    """
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


# PUBLIC_INTERFACE
def create_engine(database_url: str) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine for the application.

    Contract:
      - Inputs: database_url (postgres)
      - Outputs: AsyncEngine
      - Errors: raises ValueError if database_url is empty
      - Side effects: establishes engine configuration (no connection opened immediately)
    """
    if not database_url:
        raise ValueError("database_url is required")
    return create_async_engine(_normalize_async_database_url(database_url), pool_pre_ping=True)


# PUBLIC_INTERFACE
def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create a session factory for the app.

    Contract:
      - Inputs: AsyncEngine
      - Outputs: async_sessionmaker
      - Side effects: none
    """
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


# PUBLIC_INTERFACE
async def get_db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession.

    Contract:
      - Inputs: injected session_factory
      - Outputs: yields AsyncSession, guarantees close at end
      - Errors: propagates DB driver exceptions; caller should map at API boundary if needed
      - Side effects: opens/closes a DB session per request
    """
    async with session_factory() as session:
        yield session
