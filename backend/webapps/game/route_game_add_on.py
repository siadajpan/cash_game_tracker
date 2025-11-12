import json
from datetime import datetime
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
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
