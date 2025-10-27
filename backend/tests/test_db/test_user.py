import pytest
from sqlalchemy.orm import Session
from typing import Any, Generator
import backend.db.models.associations

# 1. Import your Pydantic schema for type hinting the fixture
from backend.schemas.user import UserCreate

# 2. Import your database functions
from backend.db.repository.user import create_new_user, get_user_by_email


# The mock_user_create_data and db_session fixtures are provided by conftest.py

# --- Database Function Tests ---


def test_create_and_get_user_success(
    db_session: Session, mock_user_create_data: UserCreate
):
    """
    Tests the creation and subsequent retrieval of a user record,
    verifying data integrity.

    This test relies on the 'db_session' and 'mock_user_create_data'
    fixtures defined in conftest.py.
    """

    # 1. Test initial state (the user should not exist)
    initial_user = get_user_by_email(email=mock_user_create_data.email, db=db_session)
    assert initial_user is None, "User should not exist before creation."

    # 2. Call the creation function
    created_user = create_new_user(user=mock_user_create_data, db=db_session)

    # 3. Assert successful creation attributes
    assert created_user is not None
    assert created_user.id is not None
    assert created_user.email == mock_user_create_data.email
    assert created_user.nick == mock_user_create_data.nick

    # Check that the password was hashed (it shouldn't match the plain text)
    assert created_user.hashed_password != mock_user_create_data.password

    # 4. Check if the user can be retrieved from the database
    retrieved_user = get_user_by_email(email=mock_user_create_data.email, db=db_session)

    # 5. Assert the retrieved user matches the created user
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.email == created_user.email


def test_get_nonexistent_user(db_session: Session):
    """
    Tests that retrieving a user with an unknown email returns None.

    This test relies on the 'db_session' fixture defined in conftest.py.
    """
    email = "unknown_user_12345@example.com"
    user = get_user_by_email(email=email, db=db_session)
    assert user is None
