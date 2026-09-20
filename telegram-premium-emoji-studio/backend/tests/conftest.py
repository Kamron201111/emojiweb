"""Shared pytest fixtures: in-memory async DB + seeded user.

These fixtures require the full dependency set (SQLAlchemy, aiosqlite,
pydantic). Run with: `pip install -r requirements.txt && pytest`.
"""
import asyncio

import pytest

try:
    import pytest_asyncio
    _asyncio_fixture = pytest_asyncio.fixture
except ImportError:  # allow stdlib-only tests to run without pytest-asyncio
    _asyncio_fixture = pytest.fixture


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@_asyncio_fixture
async def session():
    """A fresh in-memory SQLite session with all tables created."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app import models  # noqa: F401 register models

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@_asyncio_fixture
async def user(session):
    from app.models import User

    u = User(id=1001, username="tester", first_name="Test", language="uz", credits=0)
    session.add(u)
    await session.flush()
    return u
