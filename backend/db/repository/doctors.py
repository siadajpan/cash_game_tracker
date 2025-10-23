from collections import defaultdict
from typing import Dict, List, Type

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.apis.v1.route_login import get_current_user
from backend.db.models.users import User
from backend.db.models.game import Game
from backend.db.models.buy_in import BuyIn
from backend.db.repository.users import create_new_user
from backend.schemas.players import PlayerCreate
from backend.schemas.users import UserCreate


def create_new_player(user: PlayerCreate, db: Session):
    new_user = create_new_user(
        UserCreate(email=user.email, password=user.password), db
    )

    del user.email
    del user.password

    new_user = User(user_id=new_user.id, **user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def get_user(doctor_id, db):
    return db.get(User, doctor_id)


def list_all_users(db):
    users = db.query(User).all()

    return users


def list_doctors_as_show_doctor(db):
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
