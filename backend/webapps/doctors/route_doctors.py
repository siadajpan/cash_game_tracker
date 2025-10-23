import json
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from apis.v1.route_login import get_current_user_from_token, oauth2_scheme, get_current_user
from backend.db.models.doctors import DoctorSpeciality
from backend.db.repository.doctors import (
    create_new_doctor,
    get_doctor,
    get_doctors_working_hours_and_practices, list_doctors_as_show_doctor, get_doctor_by_user_id, get_current_doctor,
)
from backend.db.session import get_db
from backend.schemas.doctors import DoctorCreate, ShowDoctor
from backend.webapps.doctors.forms import DoctorCreateForm, WorkingHoursCreateForm
from backend.db.models.users import User
from db.repository.practices import retrieve_practice
from db.repository.working_hours import create_new_working_hours, get_working_hours_by_doctor_and_practice, \
    working_hours_to_dict, delete_working_hours_by_id
from webapps.practices.route_practices import read_practices

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


@router.post("/create", response_model=ShowDoctor)
def create_doctor(doctor: DoctorCreate, db: Session = Depends(get_db)):
    email = doctor.email
    new_doctor = create_new_doctor(doctor=doctor, db=db)
    # Needed for ShowDoctor class
    new_doctor.email = email

    return new_doctor


@router.get("/list", response_model=List[ShowDoctor])
def list_doctors(db: Session = Depends(get_db)):
    doctors = list_doctors_as_show_doctor(db)
    # for doctor in doctors:
    #     del doctor.hashed_password
    return doctors


@router.get("/details/{doctor_id}")
async def doctor_details(
        doctor_id: int, request: Request, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    doctors_working_hours_practices = get_doctors_working_hours_and_practices(
        doctor_id=doctor_id, db=db
    )
    doctor = get_doctor(doctor_id, db)
    if token:
        current_user = get_current_user_from_token(token, db)
        add_working_hours_visible: bool = current_user.id == doctor.user_id
    else:
        add_working_hours_visible = False

    return templates.TemplateResponse(
        "doctors/details.html",
        {
            "request": request,
            "doctor": doctor,
            "working_hours_practices": doctors_working_hours_practices,
            "add_working_hours": add_working_hours_visible,
            "edit_working_hours": add_working_hours_visible,
        },
    )


@router.get("/register/")
def register_form(request: Request):
    return templates.TemplateResponse(
        "doctors/register.html", {"request": request, "doctor_speciality": DoctorSpeciality}
    )


@router.post("/register/")
async def register(request: Request, db: Session = Depends(get_db)):
    form = DoctorCreateForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            new_doctor = DoctorCreate(
                first_name=form.first_name,
                last_name=form.last_name,
                email=form.email,
                password=form.password,
                speciality=DoctorSpeciality.DENTIST,  # TODO fix this to pass real type
            )
        except ValidationError as e:
            for error in json.loads(e.json()):
                error = f"There is are some problems with {error['loc'][0]}"
                form.errors.append(error)
            return templates.TemplateResponse("doctors/register.html", form.__dict__)
        try:
            create_new_doctor(doctor=new_doctor, db=db)
            return responses.RedirectResponse(
                "/?msg=Successfully registered", status_code=status.HTTP_302_FOUND
            )  # default is post request, to use get request added status code 302
        except IntegrityError:
            form.errors.append("User with that e-mail already exists.")
            return templates.TemplateResponse("doctors/register.html", form.__dict__)
    return templates.TemplateResponse("doctors/register.html", form.__dict__)


@router.get("/add_working_hours/")
def add_working_hours_form(request: Request, db: Session = Depends(get_db)):
    practices = read_practices(db)
    return templates.TemplateResponse(
        "doctors/add_working_hours.html", {"request": request, "practices": practices, "add_working_hours": True}
    )


@router.get("/add_working_hours_practice/{practice_id}")
def add_working_hours_practice(practice_id, request: Request, db: Session = Depends(get_db)):
    practice = retrieve_practice(practice_id=practice_id, db=db)
    doctor = get_current_doctor(request, db)
    curr_working_hours = get_working_hours_by_doctor_and_practice(doctor.id, practice_id, db)
    curr_working_hours_by_day = working_hours_to_dict(curr_working_hours)
    return templates.TemplateResponse(
        "doctors/add_working_hours_practice.html",
        {"request": request, "practice": practice, "working_hours": curr_working_hours_by_day}
    )


@router.post("/add_working_hours_practice/{practice_id}")
async def add_working_hours(practice_id, request: Request, db: Session = Depends(get_db)):
    form = WorkingHoursCreateForm(request)
    await form.load_data(practice_id)
    current_user: User = get_current_user(request, db)
    current_doctor = get_doctor_by_user_id(current_user.id, db)

    if await form.is_valid():
        curr_working_hours = get_working_hours_by_doctor_and_practice(doctor_id=current_doctor.id,
                                                                      practice_id=practice_id, db=db)
        for working_hours in curr_working_hours:
            delete_working_hours_by_id(working_hours.id, db)

        for working_hours in form.working_hours:
            working_hours.practice_id = practice_id
            create_new_working_hours(
                working_hours=working_hours, db=db, doctor_id=current_doctor.id
            )
        return responses.RedirectResponse(
            url=f"/doctors/details/{current_doctor.id}/?msg=Successfully added working hours",
            status_code=status.HTTP_302_FOUND
        )  # default is post request, to use get request added status code 302
    return templates.TemplateResponse("doctors/add_working_hours.html", form.__dict__)
