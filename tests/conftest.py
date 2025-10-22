import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from decouple import config as decouple_config

# Import your app and dependencies
from main import app, get_db
from src.user.models import UserModel

# Test database URL
TEST_DATABASE_URL = decouple_config(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@testdb:5433/test_db"
)

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    UserModel.metadata.create_all(bind=test_engine)
    
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
   
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "username": "testuser",
        "email": "test@example.com",
        "disabled": False
    }


@pytest.fixture
def mock_user_with_project(mock_user):
    """Create a mock user with project for testing."""
    user_with_project = mock_user.copy()
    user_with_project["project"] = {
        "project_id": "proj_123",
        "project_name": "Test Project"
    }
    return user_with_project


@pytest.fixture
def auth_headers(mock_user_with_project):
    """Create authorization headers for testing."""
    # Mock JWT token - in real tests you might want to create actual tokens
    return {"authorization": "Bearer mock_token_for_testing"}


@pytest.fixture
def authenticated_client(client, mock_user_with_project, monkeypatch):
    """Create an authenticated client that bypasses token verification."""
    def mock_verify_token(request, call_next):
        request.state.user = mock_user_with_project
        return call_next(request)  

    # Mock the middleware
    monkeypatch.setattr("src.main.verify_token", mock_verify_token)
    return client

