# test_user_db.py

import pytest
from sqlalchemy.orm import Session

from backend.db.repository.user import get_user_by_email, create_new_user
from backend.schemas.user import UserCreate  # Adjust import as necessary

# --- Mock Data Fixtures ---


@pytest.fixture(scope="function")
def mock_user_create_data():
    """Provides a consistent UserCreate object for testing."""

    # NOTE: You need to define the UserCreate Pydantic model
    class MockUserCreate(UserCreate):
        # We need to explicitly define required fields for the mock
        email: str = "test@example.com"
        password: str = "securepassword123"
        nick: str = "TestUserNick"

    return MockUserCreate()


# --- Database Function Tests ---


def test_create_and_get_user_success(
    db_session: Session, mock_user_create_data: UserCreate
):
    """
    Tests the creation and subsequent retrieval of a user record.
    """

    # 1. Test initial state (should not exist)
    initial_user = get_user_by_email(email=mock_user_create_data.email, db=db_session)
    assert initial_user is None, "User should not exist before creation."

    # 2. Call the creation function
    created_user = create_new_user(user=mock_user_create_data, db=db_session)

    # 3. Assert successful creation attributes
    assert created_user is not None
    assert created_user.id is not None
    assert created_user.email == mock_user_create_data.email
    assert created_user.nick == mock_user_create_data.nick
    # Password should be hashed, so it shouldn't match the plain text
    assert created_user.hashed_password != mock_user_create_data.password

    # 4. Check if the user can be retrieved from the database
    retrieved_user = get_user_by_email(email=mock_user_create_data.email, db=db_session)

    # 5. Assert the retrieved user matches the created user
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.email == created_user.email


def test_get_nonexistent_user(db_session: Session):
    """
    Tests that retrieving a non-existent user returns None.
    """
    email = "nonexistent@example.com"
    user = get_user_by_email(email=email, db=db_session)
    assert user is None
