import json
from datetime import datetime
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from backend.apis.v1.route_login import get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models.user import User
from backend.db.repository.game import create_new_game_db, get_game_by_id, user_in_game, add_user_to_game
from backend.db.repository.team import (
    create_new_user,
    get_user, get_team_by_id,
)
from backend.db.session import get_db
from backend.schemas.games import GameCreate
from backend.schemas.user import UserCreate, UserShow
from backend.webapps.game.forms import GameCreateForm, GameJoinForm

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/create", name="create_game_form")
async def create_game_form(
        request: Request,
        current_user: User = Depends(get_current_user_from_token)
):
    """
    Renders the game creation form, populating team choices and default values.
    """

    # Prepare initial form data and context for the template
    context = {
        "request": request,
        "errors": [],

        # 1. Pass the user's teams to populate the dropdown
        "user_teams": current_user.teams,

        # 2. Pass default values for the form fields
        "form": {
            "default_buy_in": 0.0,
            "date": datetime.today().date().isoformat(), # Format as YYYY-MM-DD
            "team_id": None # No team selected by default
        }
    }

    return templates.TemplateResponse("game/create.html", context)


@router.post("/create", name="create_game")
async def create_game(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_from_token),
):
    form = GameCreateForm(request)
    await form.load_data()

    default_buy_in = form.default_buy_in
    team_id = form.team_id # <-- Get the submitted team ID
    template_name = "game/create.html"
    errors = []

    # 1. Validation checks (from form.is_valid and additional checks)
    if not await form.is_valid():
        errors.extend(form.errors)

    # Re-checking validation here for clarity if form.is_valid isn't used
    if default_buy_in is None or default_buy_in < 0:
        errors.append("Default buy-in has to be 0 or more.")

    # Check if the team exists (Critical step for foreign key integrity)
    team = get_team_by_id(team_id, db)
    if not team:
        errors.append("Selected team does not exist.")

    if not errors:
        try:
            # Use all extracted variables
            date = str(datetime.today().date()) # Using today's date as a fallback, but form.date is better

            # CRITICAL: Pass the team_id to the GameCreate Pydantic model
            new_game_data = GameCreate(
                default_buy_in=default_buy_in,
                date=date,
                running=True,
                team_id=team_id,
            )

            game = create_new_game_db(game=new_game_data, current_user=current_user, db=db)

            return responses.RedirectResponse(
                f"/{game.id}/open?msg=Game created successfully",
                status_code=status.HTTP_302_FOUND
            )
        except IntegrityError:
            errors.append("A database error occurred (e.g., integrity constraint violation).")
        except Exception as e:
            errors.append(f"An unexpected error occurred: {e}")

    # Re-render with all submitted data
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "errors": errors,
            # CRITICAL FIX: Package submitted data into a 'form' object for the template
            "form": {
                "default_buy_in": default_buy_in,
                "team_id": team_id,
                # Add any other fields if you add them to the form/template
            },
            # You must also pass user_teams back for the dropdown to work
            "user_teams": current_user.teams
        }
    )

@router.get("/{game_id}/join", name="join_game_form")
async def join_game_form(
        request: Request,
        game_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user_from_token)
):
    game = get_game_by_id(game_id, db)
    # TODO Add checking if user is allowed to enter that game (if he edits href)
    if user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/open")  # already in game
    return templates.TemplateResponse("game/join.html", {"request": request, "game": game})

@router.post("/{game_id}/join", name="join_game")
async def join_game(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token)
):
    template_name = "game/join.html"
    errors = []

    # Load form data
    form = GameJoinForm(request)
    await form.load_data()
    buy_in = form.buy_in

    # Fetch game
    game = get_game_by_id(game_id, db)
    if game is None:
        errors.append("Game doesn't exist anymore. Maybe it was deleted.")

    # Validate form
    if not await form.is_valid():
        errors.extend(form.errors)

    if not errors:
        try:
            add_user_to_game(user, game, db)
            # Redirect to the game page
            return RedirectResponse(url=f"/game/{game.id}/open", status_code=303)
        except IntegrityError:
            errors.append("A database error occurred (e.g., integrity constraint violation).")
        except Exception as e:
            errors.append(f"An unexpected error occurred: {e}")

    # Re-render template with submitted data and errors
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "errors": errors,
            "game": game,
            "form": {"buy_in": buy_in},
        }
    )


@router.get("/{game_id}/open", name="open_game")
async def open_game(request: Request, game_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user_from_token)):
    print("openning game")
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet
    return templates.TemplateResponse("game/view.html", {"request": request, "game": game})

#
# @router.get("/create", response_model=UserShow)
# def create_game_endpoint(game: GameCreate, db: Session = Depends(get_db)):
#     new_game = create_new_game_db(game=game, db=db)
#
#     return new_game


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
