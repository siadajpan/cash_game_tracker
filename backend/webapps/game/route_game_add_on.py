import json
from datetime import datetime
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from backend.apis.v1.route_login import (
    get_current_user_from_token,
)
from backend.core.config import TEMPLATES_DIR
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.user import User
from backend.db.repository.add_on import (
    get_player_game_addons,
    create_add_on_request,
    update_add_on_status,
    get_add_on_by_id,
)
from backend.db.repository.buy_in import (
    get_player_game_total_buy_in_amount,
    add_user_buy_in,
    get_player_game_buy_ins,
)
from backend.db.repository.cash_out import (
    get_player_game_cash_out,
)
from backend.db.repository.game import (
    get_game_by_id,
    user_in_game,
)
from backend.db.repository.team import (
    get_team_by_id,
    is_user_admin,
)
from backend.db.session import get_db
from backend.schemas.add_on import AddOnRequest

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/{game_id}/add_on", name="add_on")
async def add_on_view(
    request: Request,
    game_id: int,
    player_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    target_player = user
    if player_id and is_user_admin(user.id, game.team_id, db):
        target_player = db.query(User).filter(User.id == player_id).first()
        if not target_player:
            raise HTTPException(status_code=404, detail="Player not found")

    return templates.TemplateResponse(
        "game/add_on.html",
        {"request": request, "game": game, "target_player": target_player, "user": user},
    )


@router.post("/{game_id}/add_on", name="add_on")
async def add_on(
    request: Request,
    game_id: int,
    player_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if game is None:
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    target_player = user
    auto_approve = False
    if player_id and (is_user_admin(user.id, game.team_id, db) or game.book_keeper_id == user.id):
        target_player = db.query(User).filter(User.id == player_id).first()
        if not target_player:
            raise HTTPException(status_code=404, detail="Player not found")
        auto_approve = True

    form = await request.form()
    print("form", form)
    errors = []
    try:
        add_on_request_form = AddOnRequest(**form)
        addon = create_add_on_request(game, add_on_request_form.add_on, db, target_player)
        if auto_approve:
            update_add_on_status(addon, PlayerRequestStatus.APPROVED, db, user)
            
        return RedirectResponse(url=f"/game/{game.id}", status_code=303)
    except ValueError:
        errors.append("Invalid add-on")
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
            "form": form,
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
    player_game_addons = get_player_game_addons(player, game, db)
    previous_addons = [
        add_on for add_on in player_game_addons if add_on.id != add_on_id
    ]
    return templates.TemplateResponse(
        "game/add_on_decide.html",
        {
            "request": request,
            "player": player,
            "buy_in": buy_in,
            "previous_addons": previous_addons,
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
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not is_user_admin(user.id, game.team_id, db):
        raise HTTPException(status_code=403, detail="Only admins can approve add-ons")

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

    # Check admin
    if not is_user_admin(user.id, game.team_id, db):
        return RedirectResponse(url=f"/game/{game.id}")

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
                "money_out": cash_out,
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
            "show_balance": True,
        },
    )
