from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.db.models.user import DoctorSpeciality
from backend.db.repository.team import list_user_view
from backend.db.session import get_db

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db), msg: str = None):
    doctors = list_user_view(db=db)

    return templates.TemplateResponse(
        "general_pages/homepage.html",
        {
            "request": request,
            "user": doctors,
            "doctor_speciality": DoctorSpeciality,
            "msg": msg,
        },
    )
