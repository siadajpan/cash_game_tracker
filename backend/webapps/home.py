from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.db.models.doctors import DoctorSpeciality
from backend.db.repository.doctors import list_doctors_as_show_doctor
from backend.db.session import get_db

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db), msg: str = None):
    doctors = list_doctors_as_show_doctor(db=db)

    return templates.TemplateResponse(
        "general_pages/homepage.html",
        {
            "request": request,
            "doctors": doctors,
            "doctor_speciality": DoctorSpeciality,
            "msg": msg,
        },
    )
