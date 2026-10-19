"""Test configuration and shared fixtures for Mound API tests."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db_session
from app.core.rate_limit import close_redis
from app.main import app
from app.models.agent import Agent
from app.models.user import User

# Use NullPool for tests so async connections close immediately within each test's event loop
test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
)
test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

settings.evidence_url_verification_enabled = False


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    """Ensures test database tables are truncated before each test."""
    async with test_session_maker() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE blueprint_amendments, blueprint_votes, blueprint_versions, "
                "blueprints, agents, users CASCADE;"
            )
        )
        await session.commit()
    yield


@pytest.fixture(autouse=True)
async def cleanup_redis() -> AsyncIterator[None]:
    """Ensures Redis connection pool is cleanly closed after each test."""
    yield
    await close_redis()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provides a transactional database session for tests.

    Yields:
        An active AsyncSession.
    """
    async with test_session_maker() as session:
        yield session


@pytest.fixture
async def test_agent(db_session: AsyncSession) -> Agent:
    """Creates a temporary test user and planning agent in the database.

    Args:
        db_session: Active database session fixture.

    Returns:
        The created Agent instance.
    """
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        github_id=f"gh_{unique_suffix}",
        username=f"tester_{unique_suffix}",
        email=f"tester_{unique_suffix}@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    agent = Agent(
        owner_id=user.id,
        name=f"TestScout_{unique_suffix}",
        description="Autonomous testing agent",
        api_key_hash=f"hash_{unique_suffix}",
        specialty_tags=["cli-tools", "testing"],
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provides an asynchronous test client overriding database session with test_session_maker.

    Yields:
        An AsyncClient configured with ASGI transport.
    """

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
