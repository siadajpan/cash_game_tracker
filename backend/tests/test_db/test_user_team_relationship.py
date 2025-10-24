import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.db.models.user import User
from backend.db.models.team import Team

def test_user_team_association(db_session: Session):
    # Create a new user
    user = User(
        email="test@example.com",
        hashed_password="hashedpassword",
        is_superuser=False,
        nick="player1",
    )

    # Create a new team
    team = Team(name="Mock Team")

    # Associate user with team (many-to-many)
    user.teams.append(team)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # --- Assertions ---
    assert len(user.teams) == 1
    assert user.teams[0].name == "Mock Team"

    db_session.refresh(team)
    assert len(team.users) == 1
    assert team.users[0].email == "test@example.com"

    result = db_session.execute(text("SELECT * FROM user_team_association")).fetchall()
    assert len(result) == 1
    assert result[0]._mapping["user_id"] == user.id
    assert result[0]._mapping["team_id"] == team.id
