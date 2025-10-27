from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text
from starlette.testclient import TestClient

from backend.db.models.user import User
from backend.db.models.team import Team


@pytest.fixture
def mock_team_create_data():
    """Provides consistent team data for testing."""
    return {"name": "Test Team"}


def test_create_team_with_owner_and_users(
    db_session: Session, mock_user_create_data, mock_team_create_data
):
    """
    Test creating a team, assigning an owner, and adding users to it.
    """

    # --- Step 1: Create owner user ---
    owner = User(
        email=mock_user_create_data.email,
        hashed_password="hashedpassword",
        nick=mock_user_create_data.nick,
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # --- Step 2: Create team ---
    team = Team(name=mock_team_create_data["name"], owner=owner)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # --- Step 3: Create additional player ---
    player = User(
        email="player2@example.com", hashed_password="hashedpassword2", nick="Player2"
    )
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

    # --- Step 4: Add player to team (Many-to-Many) ---
    team.users.append(player)
    db_session.commit()
    db_session.refresh(team)
    db_session.refresh(player)

    # --- Assertions ---
    # Owner relationship
    assert team.owner.id == owner.id
    assert owner.teams_owned[0].id == team.id

    # Many-to-Many
    assert len(team.users) == 1
    assert team.users[0].id == player.id
    assert len(player.teams) == 1
    assert player.teams[0].id == team.id

    # Optional: verify association table directly
    assoc = db_session.execute(text("SELECT * FROM user_team_association")).fetchall()
    assert len(assoc) == 1
    assert assoc[0]._mapping["user_id"] == player.id
    assert assoc[0]._mapping["team_id"] == team.id
