import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.user import User

from backend.db.session import get_db

router = APIRouter()
LOGGER = logging.getLogger(__name__)


@router.post("/create", response_model=WorkingHoursShow)
def create_working_hours(
    working_hours: WorkingHoursCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    new_working_hours = create_new_working_hours(
        working_hours=working_hours, db=db, doctor_id=current_user.id
    )

    return new_working_hours


@router.get("/get/{working_hours_id}", response_model=WorkingHoursShow)
def get_working_hours(working_hours_id, db: Session = Depends(get_db)):
    working_hours = get_working_hours_by_id(working_hours_id, db)
    if not working_hours:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Getting working hours failed. Element with id "
            f"{working_hours_id} not found",
        )
    return working_hours


@router.get("/get_doctor/{doctor_id}", response_model=List[WorkingHoursShow])
def get_user_working_hours(doctor_id, db: Session = Depends(get_db)):
    working_hours = get_working_hours_by_doctor_id(doctor_id, db)
    return working_hours


@router.put("/update/{working_hours_id}")
def update_working_hours(
    working_hours_id,
    working_hours_update: WorkingHoursCreate,
    db: Session = Depends(get_db),
):
    response = update_working_hours_by_id(working_hours_id, working_hours_update, db)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Update working hours failed. Element with id "
            f"{working_hours_id} not found",
        )
    return {"msg": "Successfully updated data."}


@router.delete("/delete/{_id}")
def delete_working_hours(_id, db: Session = Depends(get_db)):
    response = delete_working_hours_by_id(_id=_id, db=db)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deleting working hours failed. Element with id "
            f"{_id} not found",
        )
    return {"msg": "Successfully deleted data."}
