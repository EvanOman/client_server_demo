"""Test configuration and fixtures."""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.database import Base, get_db
from app.models import *  # Import all models


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session):
    """Create a test FastAPI application."""
    app = create_app()
    
    # Override database dependency
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_client(test_app):
    """Create a test HTTP client."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_tour_data():
    """Sample tour data for testing."""
    return {
        "name": "Northern Lights Adventure",
        "slug": "northern-lights-adventure",
        "description": "Experience the magical Aurora Borealis in Iceland"
    }


@pytest.fixture
def sample_departure_data():
    """Sample departure data for testing."""
    return {
        "tour_id": "tour_123",
        "starts_at": "2024-12-15T09:00:00Z",
        "capacity_total": 40,
        "price": {
            "amount": 29999,
            "currency": "USD"
        }
    }


@pytest.fixture
def sample_hold_data():
    """Sample hold data for testing."""
    return {
        "departure_id": "dep_123",
        "seats": 2,
        "customer_ref": "customer_456",
        "ttl_seconds": 600
    }