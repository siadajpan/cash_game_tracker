import json
from datetime import datetime
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
import math
from backend.apis.v1.route_login import (
    get_current_user_from_token,
)
from backend.core.config import TEMPLATES_DIR
from backend.db.models.game import Game
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.user import User
from backend.db.repository.add_on import (
    get_player_game_addons,
)
from backend.db.repository.buy_in import (
    get_player_game_total_buy_in_amount,
    add_user_buy_in,
)
from backend.db.repository.cash_out import (
    get_player_game_cash_out,
)
from backend.db.repository.chip_structure import (
    get_user_team_chip_structures_dict,
    list_team_chip_structures,
)
from backend.db.repository.game import (
    create_new_game_db,
    get_game_by_id,
    user_in_game,
    add_user_to_game,
    finish_the_game,
    get_user_game_balance,
)
from backend.db.repository.team import (
    get_team_by_id,
)
from backend.db.session import get_db
from backend.schemas.games import GameCreate, GameJoin

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/create", name="create_game_form")
async def create_game_form(
    request: Request, current_user: User = Depends(get_current_user_from_token)
):
    """
    Renders the game creation form, populating team choices and default values.
    """
    team_chip_structures = get_user_team_chip_structures_dict(current_user)
    context = {
        "request": request,
        "errors": [],
        "user_teams": current_user.teams,
        "team_chip_structures": team_chip_structures,
        "form": {
            "default_buy_in": 0.0,
            "date": datetime.today().date().isoformat(),  # Format as YYYY-MM-DD
        },
    }

    return templates.TemplateResponse("game/create.html", context)


@router.post("/create", name="create_game")
async def create_game(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    form = await request.form()
    errors = []
    try:
        # Let Pydantic handle validation
        new_game_data = GameCreate(
            date=form.get("date") or str(datetime.today().date()),
            default_buy_in=float(form.get("default_buy_in", 0)),
            running=True,
            team_id=form.get("team_id"),
            chip_structure_id=form.get("chip_structure_id"),
        )

        # Check if the team exists separately
        team = get_team_by_id(new_game_data.team_id, db)
        if not team:
            raise ValueError("Selected team does not exist.")

        # If all good, save to DB
        game = create_new_game_db(game=new_game_data, current_user=current_user, db=db)
        add_user_to_game(current_user, game, db)
        add_user_buy_in(current_user, game, new_game_data.default_buy_in, db)

        return responses.RedirectResponse(
            f"/game/{game.id}?msg=Game created successfully",
            status_code=status.HTTP_302_FOUND,
        )

    except ValidationError as e:
        # Catch Pydantic validation errors
        errors.extend([err["msg"] for err in e.errors()])
    except ValueError as e:
        # Custom logical errors (like missing team)
        errors.append(str(e))
    except IntegrityError:
        errors.append("Database integrity error occurred.")
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
    team_chip_structures = get_user_team_chip_structures_dict(current_user)

    # Render back with errors
    return templates.TemplateResponse(
        "game/create.html",
        {
            "request": request,
            "errors": errors,
            "team_chip_structures": team_chip_structures,
            "form": form,
            "user_teams": current_user.teams,
        },
    )


@router.get("/view_past", name="view_past")
async def view_past_games(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    if not user:
        return RedirectResponse(url="/login")

    # Collect all past games from all user's teams
    past_games = []
    for team in user.teams:
        for game in team.games:
            if not game.running:
                past_games.append(game)
    # Prepare data for template
    games_info = []
    for game in past_games:
        players_info = []
        for player in game.players:
            balance = get_user_game_balance(player, game, db)
            players_info.append({"player": player, "balance": balance})
        games_info.append({"game": game, "players_info": players_info})

    print(past_games)
    return templates.TemplateResponse(
        "game/view_past.html", {"request": request, "games_info": games_info}
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
        return RedirectResponse(url=f"/{game.id}")  # already in game
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
    form = await request.form()
    # Load form data
    try:
        game = get_game_by_id(game_id, db)
        buy_in=form.get("buy_in")

        form = GameJoin(buy_in=buy_in)

        # Fetch game
        if game is None:
            errors.append("Game doesn't exist anymore. Maybe it was deleted.")

        add_user_to_game(user, game, db)
        add_user_buy_in(user, game, buy_in, db)
        # Redirect to the game page
        return RedirectResponse(url=f"/game/{game.id}", status_code=303)
    
    except ValidationError as e:
        errors.extend([err['msg'] for err in e.errors()])
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
            "form": form,
        },
    )


def process_player(
    game: Game,
    player: User,
    db: Session = Depends(get_db),
):
    buy_in = get_player_game_total_buy_in_amount(player, game, db)
    add_ons_requests = get_player_game_addons(player, game, db)
    cash_out_requests = get_player_game_cash_out(player, game, db)
    cash_out_requests_non_declined = [
        c for c in cash_out_requests if c.status != PlayerRequestStatus.DECLINED
    ]

    money_in = buy_in
    money_out = None
    player_request = None
    request_href = None
    request_text = None
    can_approve = []

    if len(cash_out_requests_non_declined):
        money_out = sum(
            [
                req.amount
                for req in cash_out_requests
                if req.status == PlayerRequestStatus.APPROVED
            ]
        )
        cash_out_req = cash_out_requests[-1]

        if cash_out_req.status == PlayerRequestStatus.REQUESTED:
            player_request = cash_out_req
            request_text = f"Cash out: {cash_out_req.amount}"
            request_href = f"/game/{game.id}/cash_out/{cash_out_req.id}"
            [can_approve.append(p) for p in game.players if p.id != player.id]

    for add_on_req in add_ons_requests:
        if add_on_req.status == PlayerRequestStatus.APPROVED:
            money_in += add_on_req.amount
        elif add_on_req.status == PlayerRequestStatus.REQUESTED:
            player_request = add_on_req
            request_text = f"Add on: {add_on_req.amount}"
            request_href = f"/game/{game.id}/add_on/{add_on_req.id}"
            can_approve.append(game.owner)

    return {
        "player": player,
        "money_in": money_in,
        "money_out": money_out,
        "request": player_request,
        "request_text": request_text,
        "request_href": request_href,
        "can_approve": can_approve,
    }


@router.get("/{game_id}", name="open_game")
async def open_game(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game: Game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    players_info = []
    existing_requests = False
    for player in game.players:
        players_game_info = process_player(game, player, db)
        players_info.append(players_game_info)
        if players_game_info["request"] is not None:
            existing_requests = True
    return templates.TemplateResponse(
        "game/view_running.html",
        {
            "request": request,
            "game": game,
            "user": user,
            "players_info": players_info,
            "requests": existing_requests,
        },
    )


@router.post("/{game_id}/finish", name="finish_game_post")
async def finish_game_view(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not game:
        return RedirectResponse(url="/", status_code=303)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    finish_the_game(user, game, db)
    return RedirectResponse(url="/", status_code=303)


@router.get("/api/check_update")
def check_update(
    user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)
):
    # Get latest game in the user’s teams
    team_ids = [team.id for team in user.teams]
    latest_game = (
        db.query(Game)
        .filter(Game.team_id.in_(team_ids))
        .order_by(Game.date.desc())
        .first()
    )

    if not latest_game:
        return {"new_game": False}

    # Compare against user.last_checked_game_time if you track it, or use a simpler check
    if not hasattr(user, "last_checked_game_time") or not user.last_checked_game_time:
        user.last_checked_game_time = datetime.now()
        db.commit()
        return {"new_game": True}

    new_game = latest_game.date > user.last_checked_game_time

    if new_game:
        user.last_checked_game_time = datetime.now()
        db.commit()

    return {"new_game": new_game}
