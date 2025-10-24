from collections import defaultdict
from typing import Dict, List, Type

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.apis.v1.route_login import get_current_user
from backend.db.models.team import Team
from backend.db.models.user import User
from backend.db.models.game import Game
from backend.db.repository.user import create_new_user
from backend.schemas.team import TeamCreate


def create_new_team(team: TeamCreate, creator: User, db: Session) -> Team:
    """
    Creates a new team with the given creator as both owner and player.

    Args:
        team: TeamCreate schema object with team info.
        creator: User instance who creates the team.
        db: SQLAlchemy session.

    Returns:
        The newly created Team instance.
    """
    # 1. Create the team, set the creator as owner
    new_team = Team(
        **team.dict(),
        owner=creator  # Many-to-One owner relationship
    )

    # 2. Add the creator as a player (Many-to-Many)
    new_team.users.append(creator)

    # 3. Persist
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return new_team


def get_team_users(team: Team, db: Session) -> List[User]:
    """
    Retrieve all users (players) in a given team.

    Args:
        team: Team instance
        db: SQLAlchemy session

    Returns:
        List of User instances who are members of the team
    """
    # Option 1: Access the relationship directly (lazy-loaded)
    return team.users

    # Option 2: Query explicitly from the User table
    # return db.query(User).join(User.teams).filter(Team.id == team.id).all()

def get_user(doctor_id, db):
    return db.get(User, doctor_id)


def list_all_users(db):
    users = db.query(User).all()

    return users
