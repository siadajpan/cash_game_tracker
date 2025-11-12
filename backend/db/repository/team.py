from collections import defaultdict
from select import select
from typing import Dict, List, Type, Optional

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
    new_team = Team(**team.dict(), owner=creator)  # Many-to-One owner relationship

    # 2. Add the creator as a player (Many-to-Many)
    new_team.users.append(creator)

    # 3. Persist
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return new_team


def join_team(team_model: Team, user, db: Session) -> Team:
    """
    Adds an existing User to an existing Team's list of members
    by leveraging the many-to-many relationship defined in the models.

    Args:
        team_model: The SQLAlchemy Team model instance to join.
        user: The SQLAlchemy User model instance to be added to the team.
        db: SQLAlchemy session.

    Returns:
        The updated Team model instance.
    """
    # 1. Add the user to the team's 'users' relationship.
    # SQLAlchemy handles the creation of the record in the 'user_team_association' table.
    team_model.users.append(user)

    # 2. Persist the changes.
    # Since we modified an object already tracked by the session,
    # we just need to commit the transaction.
    db.commit()

    # 3. Refresh the team object to reflect the change, if necessary.
    db.refresh(team_model)

    return team_model


def get_team_by_name(team_name, db: Session):
    return db.query(Team).filter(Team.name == team_name).one_or_none()


def check_team_exists(team_name: str, db: Session) -> bool:
    """
    Check if a team with the given name exists in the database.

    Args:
        team_name: Name of the team to check.
        db: SQLAlchemy session.

    Returns:
        True if the team exists, False otherwise.
    """
    team = db.query(Team).filter(Team.name == team_name).one_or_none()
    return team is not None


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


def get_team_by_id(team_id: int, db: Session) -> Optional[Team]:
    """
    Fetches a Team model instance by its ID.

    NOTE: In a real application, this function should be moved to services/team.py.
    """
    # Use select statement to query the database
    # The Team model must be imported/available for this to work
    return db.query(Team).filter(Team.id == team_id).one_or_none()


def get_user(doctor_id, db):
    return db.get(User, doctor_id)


def list_all_users(db):
    users = db.query(User).all()

    return users
