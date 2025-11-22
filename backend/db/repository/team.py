from collections import defaultdict
from multiprocessing import Value
from select import select
from sqlite3 import IntegrityError
from typing import Dict, List, Type, Optional
import random

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.apis.v1.route_login import get_current_user
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.team import Team
from backend.db.models.user import User
from backend.db.models.game import Game
from backend.db.models.user_team import UserTeam
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
    new_team = Team(**team.model_dump(), owner=creator)

    team_association = UserTeam(
        user=creator,
        team=new_team,
        status=PlayerRequestStatus.APPROVED,  # auto approve when creating a team
    )

    creator.team_associations.append(team_association)

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
    team_association = UserTeam(
        user=user,
        team=team_model,
        status=PlayerRequestStatus.REQUESTED,  # team owner needs to approve it
    )

    user.team_associations.append(team_association)
    db.commit()
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
    """
    return db.query(Team).filter(Team.id == team_id).one_or_none()


def generate_team_code(
    db: Session, min_digits: int = 4, max_digits=8, max_attempts: int = 100
) -> str:
    """
    Generate a unique numeric team code.
    Starts with 4 digits, expands if all are taken.
    """
    digits = min_digits

    for _ in range(max_digits - min_digits):
        # generate a few random codes at this digit length
        for _ in range(max_attempts):
            code_int = random.randint(0, 10**digits - 1)
            code = f"{code_int:0{digits}d}"  # zero-padded

            # Check if it exists
            exists = db.query(Team).filter_by(search_code=code).first()
            if not exists:
                return code

        # if all attempts failed, increase digit count
        digits += 1
        print(
            f"All {digits-1}-digit codes exhausted, switching to {digits}-digit codes."
        )

    raise ValueError("Can't generate the team code, try again.")


def get_team_by_search_code(search_code: str, db: Session) -> Optional[Team]:
    """
    Fetches a Team model instance by its ID.
    """
    return db.query(Team).filter(Team.search_code == search_code).one_or_none()


def get_user(doctor_id, db):
    return db.get(User, doctor_id)


def list_all_users(db):
    users = db.query(User).all()

    return users
