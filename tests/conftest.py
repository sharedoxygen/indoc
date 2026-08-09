"""
Pytest configuration and fixtures for inDoc tests
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient
from fastapi import FastAPI

from app.main import app
from app.models.base import Base
from app.db.session import get_db
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.document import Document
from app.core.security import get_password_hash, create_access_token


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def test_app(test_db: AsyncSession) -> FastAPI:
    """Create test FastAPI app with test database"""
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=False
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_token(client: AsyncClient, test_user: User) -> str:
    """Obtain JWT token via login endpoint for test_user"""
    login_data = {"username": test_user.email, "password": "testpassword"}
    response = await client.post(
        "/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = response.json().get("access_token")
    return token


@pytest.fixture
async def test_admin_user(test_db: AsyncSession) -> User:
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def test_uploader_user(test_db: AsyncSession) -> User:
    """Create a test uploader user"""
    uploader = User(
        email="uploader@example.com",
        username="uploader",
        full_name="Uploader User",
        hashed_password=get_password_hash("uploaderpassword"),
        role=UserRole.UPLOADER,
        is_active=True,
        is_verified=True
    )
    test_db.add(uploader)
    await test_db.commit()
    await test_db.refresh(uploader)
    return uploader


@pytest.fixture
async def test_manager_user(test_db: AsyncSession) -> User:
    """Create a test manager user"""
    manager = User(
        email="manager@example.com",
        username="manager",
        full_name="Manager User",
        hashed_password=get_password_hash("managerpassword"),
        role=UserRole.MANAGER,
        is_active=True,
        is_verified=True
    )
    test_db.add(manager)
    await test_db.commit()
    await test_db.refresh(manager)
    return manager


@pytest.fixture
async def test_analyst_user(test_db: AsyncSession, test_manager_user: User) -> User:
    """Create a test analyst user assigned to test_manager_user"""
    analyst = User(
        email="analyst@example.com",
        username="analyst",
        full_name="Analyst User",
        hashed_password=get_password_hash("analystpassword"),
        role=UserRole.ANALYST,
        is_active=True,
        is_verified=True,
        manager_id=test_manager_user.id
    )
    test_db.add(analyst)
    await test_db.commit()
    await test_db.refresh(analyst)
    return analyst


@pytest.fixture
def admin_token(test_admin_user: User) -> str:
    """Create admin JWT token"""
    return create_access_token(data={"sub": test_admin_user.email, "role": test_admin_user.role.value})


@pytest.fixture
def uploader_token(test_uploader_user: User) -> str:
    """Create uploader JWT token"""
    return create_access_token(data={"sub": test_uploader_user.email, "role": test_uploader_user.role.value})


@pytest.fixture
async def test_document(test_db: AsyncSession, test_user: User) -> Document:
    """Create a test document"""
    document = Document(
        filename="test_document.pdf",
        file_type="pdf",
        file_size=1024,
        file_hash="abcd1234567890",
        storage_path="/tmp/test_document.pdf",
        status="indexed",
        title="Test Document",
        description="A test document for unit tests",
        uploaded_by=test_user.id
    )
    test_db.add(document)
    await test_db.commit()
    await test_db.refresh(document)
    return document


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    test_settings = settings.copy()
    test_settings.ENABLE_FIELD_ENCRYPTION = False  # Disable for testing
    test_settings.JWT_SECRET_KEY = "test-secret-key-for-testing-only"
    return test_settings
