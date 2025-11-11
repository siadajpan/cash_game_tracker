import json
from datetime import datetime
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from urllib3 import request

from backend.apis.v1.route_login import (
    get_current_user_from_token,
)
from backend.core.config import TEMPLATES_DIR
from backend.db.models.add_on import PlayerRequestStatus
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.repository.add_on import (
    get_player_game_addons,
    create_add_on_request,
    update_add_on_status,
    get_add_on_by_id,
    get_player_game_total_approved_add_on_amount,
)
from backend.db.repository.buy_in import (
    get_player_game_total_buy_in_amount,
    add_user_buy_in,
    get_player_game_buy_ins,
)
from backend.db.repository.cash_out import (
    create_cash_out_request,
    get_player_game_cash_out,
    get_cash_out_by_id,
    update_cash_out_status,
)
from backend.db.repository.chip_structure import list_team_chip_structures
from backend.db.repository.game import (
    create_new_game_db,
    get_game_by_id,
    user_in_game,
    add_user_to_game,
    finish_the_game,
    get_user_game_balance,
)
from backend.db.repository.team import (
    create_new_user,
    get_user,
    get_team_by_id,
)
from backend.db.session import get_db
from backend.schemas import chip_structure
from backend.schemas.games import GameCreate
from backend.schemas.user import UserCreate, UserShow
from backend.webapps.game.game_forms import (
    GameCreateForm,
    GameJoinForm,
    AddOnRequest,
    CashOutRequest,
)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/create", name="create_game_form")
async def create_game_form(
    request: Request, current_user: User = Depends(get_current_user_from_token)
):
    """
    Renders the game creation form, populating team choices and default values.
    """
    team_chip_structures = {}
    for team in current_user.teams:
        team_chip_structures[team.id] = [
            {"id": cs.id, "name": str(cs.name)} for cs in team.chip_structure
        ]
        # print(
        #     "team:",
        #     team.name,
        #     "chip structures:",
        #     [cs.name for cs in team.chip_structure],
        # )
    team_chip_structures = json.dumps(team_chip_structures)
    print("Chip structures of the user:", team_chip_structures)
    # Prepare initial form data and context for the template
    context = {
        "request": request,
        "errors": [],
        # 1. Pass the user's teams to populate the dropdown
        "user_teams": current_user.teams,

        "team_chip_structures": team_chip_structures,
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
            add_user_to_game(current_user, game, db)
            add_user_buy_in(current_user, game, default_buy_in, db)

            return responses.RedirectResponse(
                f"/game/{game.id}?msg=Game created successfully",
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
            add_user_buy_in(user, game, buy_in, db)
            # Redirect to the game page
            return RedirectResponse(url=f"/game/{game.id}", status_code=303)
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
        cash_out_req = cash_out_requests[-1]
        if cash_out_req.status == PlayerRequestStatus.APPROVED:
            money_out = cash_out_req.amount
        elif cash_out_req.status == PlayerRequestStatus.REQUESTED:
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


@router.get("/{game_id}/cash_out/{cash_out_id}", name="add_on")
async def cash_out_view(
    request: Request,
    game_id: int,
    cash_out_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet
    cash_out_request = get_cash_out_by_id(cash_out_id, db)
    player = cash_out_request.user
    buy_in = get_player_game_total_buy_in_amount(player, game, db)
    add_on = get_player_game_total_approved_add_on_amount(player, game, db)
    return templates.TemplateResponse(
        "game/cash_out_decide.html",
        {
            "request": request,
            "player": player,
            "money_in": buy_in + add_on,
            "cash_out_request": cash_out_request,
            "game_id": game_id,
        },
    )


@router.get("/{game_id}/add_on", name="add_on")
async def add_on_view(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    return templates.TemplateResponse(
        "game/add_on.html",
        {"request": request, "game": game},
    )


@router.post("/{game_id}/add_on", name="add_on")
async def add_on(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    # Load form data
    form = AddOnRequest(request)
    await form.load_data()
    amount = form.amount

    errors = []
    # Fetch game
    game = get_game_by_id(game_id, db)
    if game is None:
        errors.append("Game doesn't exist anymore. Maybe it was deleted.")

    # Validate form
    if not await form.is_valid():
        errors.extend(form.errors)

    if not errors:
        try:
            create_add_on_request(game, amount, db, user)
            # Redirect to the game page
            return RedirectResponse(url=f"/game/{game.id}", status_code=303)
        except IntegrityError:
            errors.append(
                "A database error occurred (e.g., integrity constraint violation)."
            )
        except Exception as e:
            errors.append(f"An unexpected error occurred: {e}")

    # Re-render template with submitted data and errors
    return templates.TemplateResponse(
        "game/add_on.html",
        {
            "request": request,
            "errors": errors,
            "game": game,
            "form": {"amount": amount},
        },
    )


@router.get("/{game_id}/add_on/{add_on_id}", name="add_on_decide")
async def add_on_approve(
    request: Request,
    game_id: int,
    add_on_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet
    add_on_request = get_add_on_by_id(add_on_id, db)
    player = add_on_request.user
    buy_in = get_player_game_total_buy_in_amount(player, game, db)
    return templates.TemplateResponse(
        "game/add_on_decide.html",
        {
            "request": request,
            "player": player,
            "buy_in": buy_in,
            "add_on_request": add_on_request,
            "game_id": game_id,
        },
    )


@router.post("/{game_id}/add_on/{add_on_id}/{action}", name="add_on_approve")
async def add_on_approve(
    request: Request,
    game_id: int,
    add_on_id: int,
    action: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    # TODO check if current user is game owner
    action = (
        PlayerRequestStatus.APPROVED
        if action == "approve"
        else PlayerRequestStatus.DECLINED
    )
    add_on = get_add_on_by_id(add_on_id, db)
    update_add_on_status(add_on, action, db, user)

    return RedirectResponse(url=f"/game/{game.id}", status_code=303)


@router.get("/{game_id}/cash_out", name="cash_out")
async def add_on(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    return templates.TemplateResponse(
        "game/cash_out.html",
        {"request": request, "game": game},
    )


@router.post("/{game_id}/cash_out", name="cash_out")
async def add_on(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    # Load form data
    form = CashOutRequest(request)
    await form.load_data()
    amount = form.amount

    errors = []
    # Fetch game
    game = get_game_by_id(game_id, db)
    if game is None:
        errors.append("Game doesn't exist anymore. Maybe it was deleted.")

    # Validate form
    if not await form.is_valid():
        errors.extend(form.errors)

    if not errors:
        try:
            create_cash_out_request(game, amount, db, user)
            # Redirect to the game page
            return RedirectResponse(url=f"/game/{game.id}", status_code=303)
        except IntegrityError:
            errors.append(
                "A database error occurred (e.g., integrity constraint violation)."
            )
        except Exception as e:
            errors.append(f"An unexpected error occurred: {e}")

    # Re-render template with submitted data and errors
    return templates.TemplateResponse(
        f"game/cash_out.html",
        {
            "request": request,
            "errors": errors,
            "game": game,
            "form": {"cash_out": amount},
        },
    )


@router.post("/{game_id}/cash_out/{cash_out_id}/{action}", name="cash_out_approve")
async def cash_out_approve(
    request: Request,
    game_id: int,
    cash_out_id: int,
    action: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    # TODO check if current user is game owner
    action = (
        PlayerRequestStatus.APPROVED
        if action == "approve"
        else PlayerRequestStatus.DECLINED
    )
    cash_out = get_cash_out_by_id(cash_out_id, db)
    update_cash_out_status(cash_out, action, db, user)

    return RedirectResponse(url=f"/game/{game.id}", status_code=303)


@router.get("/{game_id}/finish", name="finish_game_view")
async def finish_game_view(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not game:
        return RedirectResponse(url="/")

    # Check owner
    if game.owner_id != user.id:
        return RedirectResponse(url=f"/game/{game.id}/open")

    players_info = []
    all_cashed_out = True
    total_money_in = 0
    total_money_out = 0

    for player in game.players:
        buy_ins = get_player_game_buy_ins(player, game, db)
        add_ons = get_player_game_addons(player, game, db)
        cash_outs = get_player_game_cash_out(player, game, db)

        buy_in_sum = sum([bi.amount for bi in buy_ins])
        add_on_sum = sum(
            [ao.amount for ao in add_ons if ao.status == PlayerRequestStatus.APPROVED]
        )
        money_in = buy_in_sum + add_on_sum
        cash_out = sum(
            [co.amount for co in cash_outs if co.status == PlayerRequestStatus.APPROVED]
        )
        balance = cash_out - money_in

        if len(cash_outs) < len(buy_ins):
            all_cashed_out = False

        total_money_in += money_in
        total_money_out += cash_out

        players_info.append(
            {
                "player": player,
                "money_in": money_in,
                "cash_out": cash_out,
                "balance": balance,
            }
        )

    sum_warning = total_money_in != total_money_out

    return templates.TemplateResponse(
        "game/finish.html",
        {
            "request": request,
            "game": game,
            "players_info": players_info,
            "all_cashed_out": all_cashed_out,
            "sum_warning": sum_warning,
            "total_buy_in": total_money_in,
            "total_cash_out": total_money_out,
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
