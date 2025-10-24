import json
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette import status

from backend.apis.v1.route_login import get_current_user, get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models.user import User
from backend.db.repository.team import (
    create_new_user,
    get_user, create_new_team,
)
from backend.db.session import get_db
from backend.schemas.team import TeamCreate
from backend.schemas.user import UserCreate, UserShow
from backend.webapps.team.forms import TeamCreateForm
import os

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter()

@router.get("/create")
async def create_form(request: Request):
    # Provide empty defaults for form fields and errors
    context = {
        "request": request,
        "errors": [],
        "name": "",
    }
    return templates.TemplateResponse("team/create.html", context)

@router.post("/create", name="create_team")
async def create_team(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    # ... rest of your original custom form loading code ...
    form = TeamCreateForm(request)
    await form.load_data()

    name = form.name
    template_name = "team/create.html"
    errors = []

    # 1. Validation for name
    if not name:
        errors.append("Team name is required.")

    # 2. Add validation for new fields if necessary
    # if len(description) < 10:
    #     errors.append("Description is too short.")

    if not errors:
        try:
            # Use all extracted variables
            new_team_data = TeamCreate(name=name) # Update your Pydantic model
            create_new_team(team=new_team_data, creator=current_user, db=db)
            return responses.RedirectResponse(
                "/?msg=Team created successfully",
                status_code=status.HTTP_302_FOUND
            )
        except IntegrityError:
            errors.append("Team with that name already exists.")

    # Re-render with all submitted data
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "errors": errors,
            "name": name,
        }
    )



@router.get("/list", response_model=List[UserShow])
def list_users(db: Session = Depends(get_db)):
    users = list_user_view(db)
    # for doctor in user:
    #     del doctor.hashed_password
    return users

#
# @router.get("/details/{doctor_id}")
# async def doctor_details(
#         doctor_id: int, request: Request, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
# ):
#     doctors_working_hours_practices = get_doctors_working_hours_and_practices(
#         doctor_id=doctor_id, db=db
#     )
#     doctor = get_user(doctor_id, db)
#     if token:
#         current_user = get_current_user_from_token(token, db)
#         add_working_hours_visible: bool = current_user.id == doctor.user_id
#     else:
#         add_working_hours_visible = False
#
#     return templates.TemplateResponse(
#         "user/details.html",
#         {
#             "request": request,
#             "doctor": doctor,
#             "working_hours_practices": doctors_working_hours_practices,
#             "add_working_hours": add_working_hours_visible,
#             "edit_working_hours": add_working_hours_visible,
#         },
#     )
#
#
# @router.get("/register/")
# def register_form(request: Request):
#     return templates.TemplateResponse(
#         "user/create.html", {"request": request, "doctor_speciality": DoctorSpeciality}
#     )
#
#
# @router.post("/register/")
# async def register(request: Request, db: Session = Depends(get_db)):
#     form = UserCreateForm(request)
#     await form.load_data()
#     if await form.is_valid():
#         try:
#             new_user = UserCreate(
#                 email=form.email,
#                 nick=form.nick,
#                 password=form.password,
#             )
#         except ValidationError as e:
#             for error in json.loads(e.json()):
#                 error = f"There is are some problems with {error['loc'][0]}"
#                 form.errors.append(error)
#             return templates.TemplateResponse("user/create.html", form.__dict__)
#         try:
#             create_new_user(user=new_user, db=db)
#             return responses.RedirectResponse(
#                 "/?msg=Successfully registered", status_code=status.HTTP_302_FOUND
#             )  # default is post request, to use get request added status code 302
#         except IntegrityError:
#             form.errors.append("User with that e-mail already exists.")
#             return templates.TemplateResponse("user/create.html", form.__dict__)
#     return templates.TemplateResponse("user/create.html", form.__dict__)
#
#
# @router.get("/create_team/")
# def add_working_hours_form(request: Request, db: Session = Depends(get_db)):
#     team = read_practices(db)
#     return templates.TemplateResponse(
#         "user/add_working_hours.html", {"request": request, "team": team, "add_working_hours": True}
#     )
#
#
# @router.get("/add_working_hours_practice/{practice_id}")
# def add_working_hours_practice(practice_id, request: Request, db: Session = Depends(get_db)):
#     practice = retrieve_practice(practice_id=practice_id, db=db)
#     doctor = get_current_doctor(request, db)
#     curr_working_hours = get_working_hours_by_doctor_and_practice(doctor.id, practice_id, db)
#     curr_working_hours_by_day = working_hours_to_dict(curr_working_hours)
#     return templates.TemplateResponse(
#         "user/add_working_hours_practice.html",
#         {"request": request, "practice": practice, "working_hours": curr_working_hours_by_day}
#     )
#
#
# @router.post("/add_working_hours_practice/{practice_id}")
# async def add_working_hours(practice_id, request: Request, db: Session = Depends(get_db)):
#     form = WorkingHoursCreateForm(request)
#     await form.load_data(practice_id)
#     current_user: User = get_current_user(request, db)
#     current_doctor = get_doctor_by_user_id(current_user.id, db)
#
#     if await form.is_valid():
#         curr_working_hours = get_working_hours_by_doctor_and_practice(doctor_id=current_doctor.id,
#                                                                       practice_id=practice_id, db=db)
#         for working_hours in curr_working_hours:
#             delete_working_hours_by_id(working_hours.id, db)
#
#         for working_hours in form.working_hours:
#             working_hours.practice_id = practice_id
#             create_new_working_hours(
#                 working_hours=working_hours, db=db, doctor_id=current_doctor.id
#             )
#         return responses.RedirectResponse(
#             url=f"/user/details/{current_doctor.id}/?msg=Successfully added working hours",
#             status_code=status.HTTP_302_FOUND
#         )  # default is post request, to use get request added status code 302
#     return templates.TemplateResponse("user/add_working_hours.html", form.__dict__)
