from typing import Any, Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from requests import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.schemas.team import TeamCreate
from backend.schemas.user import UserCreate
from backend.apis.base import api_router
from backend.core.config import settings
from backend.db.base_class import Base
from backend.db.session import get_db
from backend.tests.utils.users import login_test_user

import backend.db.base  # noqa - imports all the tables


def start_application():
    app = FastAPI()
    app.include_router(api_router)
    return app


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
# Use connect_args parameter only with sqlite
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def app() -> Generator[FastAPI, Any, None]:
    """
    Creates a fresh database on each test case. This is where Base.metadata.create_all()
    must be called, after all models have been imported above.
    """
    Base.metadata.create_all(engine)  # Create the tables.
    _app = start_application()
    yield _app
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(app: FastAPI) -> Generator[SessionTesting, Any, None]:
    """
    Creates a new database session with a transaction that is rolled back after
    each test, ensuring isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionTesting(bind=connection)
    yield session  # use the session in tests.
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(
    app: FastAPI, db_session: SessionTesting
) -> Generator[TestClient, Any, None]:
    """
    Creates a new FastAPI TestClient that overrides the `get_db` dependency
    to use the test database session.
    """

    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def user_logged_in(client: TestClient, db_session: Session):
    """Logs in a test user for API testing."""
    login_test_user(
        client=client, email=settings.TEST_USER_EMAIL
    )

@pytest.fixture(scope="function")
def mock_user_create_data() -> UserCreate:
    """
    Provides a consistent UserCreate object for testing by instantiating 
    the Pydantic model directly.
    """
    # Simply create and return an instance of the Pydantic model
    return UserCreate(
        email="test@example.com",
        password="securepassword123",
        nick="TestUserNick"
    )


@pytest.fixture(scope="function")
def mock_team_create_data() -> TeamCreate:
    """
    Provides a consistent UserCreate object for testing by instantiating
    the Pydantic model directly.
    """
    # Simply create and return an instance of the Pydantic model
    return TeamCreate(
        name="TestGame",
    )
