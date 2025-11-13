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
from backend.db.models.team import Team
from backend.db.models.user import User
from backend.db.repository.game import get_user_games_count, get_user_total_balance
from backend.db.repository.team import (
    create_new_user,
    generate_team_code,
    get_team_by_search_code,
    get_user,
    create_new_team,
    join_team,
    get_team_by_name,
)
from backend.db.session import get_db
from backend.schemas.team import TeamCreate
from backend.schemas.user import UserCreate, UserShow
from backend.webapps.team.forms import TeamCreateForm, TeamJoinForm
import os
from sqlalchemy import select

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

    team_search_code = generate_team_code(db)
    if not errors:
        try:
            # Use all extracted variables
            new_team_data = TeamCreate(
                name=name, search_code=team_search_code
            )  # Update your Pydantic model
            create_new_team(team=new_team_data, creator=current_user, db=db)
            return responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        except IntegrityError:
            errors.append("Team with that name already exists.")

    # Re-render with all submitted data
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "errors": errors,
            "name": name,
        },
    )


@router.get("/join")
async def join_form(request: Request):
    # Provide empty defaults for form fields and errors
    context = {
        "request": request,
        "errors": [],
        "name": "",
    }
    return templates.TemplateResponse("team/join.html", context)


@router.post("/join", name="join_team")
async def join_team_post(  # Renamed function to avoid conflict with service function
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    # Load form data using your custom loader
    form = TeamJoinForm(request)
    await form.load_data()

    search_code = form.search_code
    template_name = "team/join.html"
    errors = []

    # 1. Validation for name submission
    if not search_code:
        errors.append("Team search code is required.")

    if not errors:
        # 2. Find the team in the database
        team_model = get_team_by_search_code(search_code, db)

        if not team_model:
            errors.append(f"Team with code '{search_code}' not found.")
        elif current_user in team_model.users:
            errors.append(
                f"You are already a member of team {team_model.name}#{search_code}."
            )
        else:
            # 3. Use the imported service function to join the team
            try:
                join_team(team_model=team_model, user=current_user, db=db)

                return responses.RedirectResponse(
                    "/?msg=Successfully joined team", status_code=status.HTTP_302_FOUND
                )
            except Exception as e:
                # Handle unexpected DB errors during the join process
                errors.append(
                    f"An unexpected error occurred while joining the team: {e}"
                )

    # Re-render with errors
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "errors": errors,
            "search_code": search_code,
        },
    )


@router.get("/{team_id}")
async def team_view(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {"error": "Team not found"}

    players_info = []
    for player in team.users:
        games_count = get_user_games_count(player, db)
        total_balance = get_user_total_balance(player, db)
        players_info.append(
            {
                "player": player,
                "games_count": games_count,
                "total_balance": total_balance,
            }
        )

    return templates.TemplateResponse(
        "team/team_view.html",
        {"request": request, "team": team, "players_info": players_info},
    )


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
