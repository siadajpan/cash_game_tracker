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
from backend.db.repository.addon import get_player_game_addons
from backend.db.repository.buyin import get_player_game_buy_in
from backend.db.repository.game import (
    create_new_game_db,
    get_game_by_id,
    user_in_game,
    add_user_to_game,
)
from backend.db.repository.team import (
    create_new_user,
    get_user,
    get_team_by_id,
)
from backend.db.session import get_db
from backend.schemas.games import GameCreate
from backend.schemas.user import UserCreate, UserShow
from backend.webapps.game.forms import GameCreateForm, GameJoinForm

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/create", name="create_game_form")
async def create_game_form(
    request: Request, current_user: User = Depends(get_current_user_from_token)
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
            "date": datetime.today().date().isoformat(),  # Format as YYYY-MM-DD
            "team_id": None,  # No team selected by default
        },
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
    team_id = form.team_id  # <-- Get the submitted team ID
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
            date = str(
                datetime.today().date()
            )  # Using today's date as a fallback, but form.date is better

            # CRITICAL: Pass the team_id to the GameCreate Pydantic model
            new_game_data = GameCreate(
                default_buy_in=default_buy_in,
                date=date,
                running=True,
                team_id=team_id,
            )

            game = create_new_game_db(
                game=new_game_data, current_user=current_user, db=db
            )

            return responses.RedirectResponse(
                f"/{game.id}/open?msg=Game created successfully",
                status_code=status.HTTP_302_FOUND,
            )
        except IntegrityError:
            errors.append(
                "A database error occurred (e.g., integrity constraint violation)."
            )
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
            "user_teams": current_user.teams,
        },
    )


@router.get("/{game_id}/join", name="join_game_form")
async def join_game_form(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    # TODO Add checking if user is allowed to enter that game (if he edits href)
    if user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/open")  # already in game
    return templates.TemplateResponse(
        "game/join.html", {"request": request, "game": game}
    )


@router.post("/{game_id}/join", name="join_game")
async def join_game(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
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
            errors.append(
                "A database error occurred (e.g., integrity constraint violation)."
            )
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
        },
    )


@router.get("/{game_id}/open", name="open_game")
async def open_game(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    print("openning game")
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    players_info = []
    for player in game.players:
        buy_in = get_player_game_buy_in(user, game, db)
        add_ons = get_player_game_addons(user, game, db)
        players_info.append({"player": player, "Money-in": buy_in + add_ons})
    return templates.TemplateResponse(
        "game/view.html",
        {"request": request, "game": game, "players_info": players_info},
    )
