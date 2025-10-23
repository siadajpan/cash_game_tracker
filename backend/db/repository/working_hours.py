from collections import defaultdict
from typing import List, Type, Dict

from sqlalchemy.orm import Session

from backend.db.models.working_hours import WorkingHours
from backend.schemas.working_hours import WorkingHoursCreate
from webapps.utils.types import DAYS


def create_new_working_hours(
        working_hours: WorkingHoursCreate, db: Session, doctor_id: int
):
    # TODO How to validate start and end time?
    # WorkingHoursCreate.validate_start_less_than_end(
    #     working_hours.start_time, working_hours.end_time
    # )
    new_working_hours = WorkingHours(
        doctor_id=doctor_id,
        **working_hours.dict(),
    )
    db.add(new_working_hours)
    db.commit()
    db.refresh(new_working_hours)

    return new_working_hours


def get_working_hours_by_id(working_hours_id: int, db: Session):
    hours = db.get(WorkingHours, working_hours_id)
    return hours or None


def update_working_hours_by_id(
        working_hours_id: int, working_hours: WorkingHoursCreate, db: Session
):
    existing_hours = db.get(WorkingHours, working_hours_id)
    if not existing_hours:
        return 0
    update_data = working_hours.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing_hours, key, value)

    db.add(existing_hours)
    db.commit()
    db.refresh(existing_hours)
    return 1


def delete_working_hours_by_id(_id: int, db: Session):
    working_hours = db.get(WorkingHours, _id)
    if not working_hours:
        return 0

    db.delete(working_hours)
    db.commit()
    return 1


def get_working_hours_by_doctor_id(doctor_id: int, db: Session):
    doctors_working_hours = (
        db.query(WorkingHours).filter(WorkingHours.doctor_id == doctor_id).all()
    )
    return doctors_working_hours


def get_working_hours_by_practice_id(practice_id: int, db: Session):
    practice_working_hours = (
        db.query(WorkingHours).filter(WorkingHours.practice_id == practice_id).all()
    )
    return practice_working_hours


def get_working_hours_by_doctor_and_practice(doctor_id: int, practice_id: int, db: Session) \
        -> List[Type[WorkingHours]]:
    working_hours = (
        db.query(WorkingHours)
        .filter(WorkingHours.doctor_id == doctor_id)
        .filter(WorkingHours.practice_id == practice_id)
        .all()
    )
    return working_hours


def working_hours_to_dict(working_hours: List[Type[WorkingHours]]) -> Dict[str, List[WorkingHours]]:
    working_hours_by_day = defaultdict(list)
    for day in DAYS:
        working_hours_from_this_day = [wh for wh in working_hours if wh.day_of_week == day]
        working_hours_by_day[day] = working_hours_from_this_day
    return working_hours_by_day
