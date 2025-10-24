from collections import defaultdict
from typing import Dict, List, Type

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.apis.v1.route_login import get_current_user
from backend.db.models.team import Team
from backend.db.models.user import User
from backend.db.models.game import Game
from backend.db.models.buy_in import BuyIn
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


def get_user(doctor_id, db):
    return db.get(User, doctor_id)


def list_all_users(db):
    users = db.query(User).all()

    return users


def list_user_view(db):
    doctors_and_users = db.query(User, User).join(User).all()
    if not len(doctors_and_users):
        return []

    # Show doctor expects an email
    for doctor, user in doctors_and_users:
        doctor.date = user.date
    return list(zip(*doctors_and_users))[0]


# def sort_working_hours(working_hours_list: List[WorkingHours]) -> List[WorkingHours]:
#     for day in DAYS:
#
#     return working_hours_list


def get_doctors_working_hours_and_practices(doctor_id: int, db) \
        -> Dict[Game, List[BuyIn]]:
    practices_working_hours = (
        db.query(Game, BuyIn)
        .join(BuyIn)
        .filter(BuyIn.doctor_id == doctor_id)
        .all()
    )
    practice_groups = defaultdict(list)
    for practice, working_hours in practices_working_hours:
        practice_groups[practice].append(working_hours)

    # for practice, working_hours in practice_groups.items():
    #     practice_groups[practice] = sort_working_hours(working_hours)

    return practice_groups


def retrieve_practice_doctors_and_working_hours(practice_id: int, db: Session) \
        -> Dict[User, List[BuyIn]]:
    doctors_working_hours = (
        db.query(User, BuyIn)
        .join(BuyIn)
        .filter(BuyIn.practice_id == practice_id)
        .all()
    )
    doctors_groups = defaultdict(list)
    for doctor, working_hours in doctors_working_hours:
        doctors_groups[doctor].append(working_hours)

    return doctors_groups


def get_doctor_by_user_id(user_id: int, db: Session) -> Type[User]:
    doctor = (
        db.query(User)
        .where(User.user_id == user_id)
        .one()
    )
    return doctor


def get_current_doctor(request: Request, db: Session):
    current_user = get_current_user(request, db)
    current_doctor = get_doctor_by_user_id(user_id=current_user.id, db=db)
    return current_doctor
