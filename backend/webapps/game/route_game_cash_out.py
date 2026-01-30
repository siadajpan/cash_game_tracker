from sqlite3 import IntegrityError
from typing import List
from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from pydantic_core import PydanticCustomError, ValidationError
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from backend.db.models.chip import Chip
from backend.schemas.chip_amount import ChipAmountCreate

from backend.apis.v1.route_login import (
    get_current_user_from_token,
)
from backend.core.config import TEMPLATES_DIR
from backend.db.models.add_on import PlayerRequestStatus
from backend.db.models.user import User
from backend.db.repository.add_on import (
    get_player_game_total_approved_add_on_amount,
)
from backend.db.repository.buy_in import (
    get_player_game_total_buy_in_amount,
)
from backend.db.repository.cash_out import (
    create_cash_out_request,
    get_cash_out_by_id,
    update_cash_out_status,
)
from backend.db.repository.chip_structure import (
    get_chip_structure_as_list,
    get_chips_from_structure,
)
from backend.db.repository.game import (
    get_game_by_id,
    user_in_game,
)
from backend.db.repository.team import (
    is_user_admin,
)
from backend.db.session import get_db
from backend.schemas.cash_out import (
    CashOutByAmountRequest,
    CashOutRequest,
)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/{game_id}/cash_out", name="cash_out")
async def cash_out(
    request: Request,
    game_id: int,
    player_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet
    chip_structure = get_chip_structure_as_list(game.chip_structure_id, db)

    target_player = user
    if player_id and (is_user_admin(user.id, game.team_id, db) or user.id == game.owner_id or user.id == game.book_keeper_id):
        target_player = db.query(User).filter(User.id == player_id).first()
        if not target_player:
            raise HTTPException(status_code=404, detail="Player not found")

    return templates.TemplateResponse(
        "game/cash_out.html",
        context={
            "request": request,
            "game_id": game.id,
            "chip_structure": chip_structure,
            "target_player": target_player,
            "user": user,
        },
    )


@router.get("/{game_id}/cash_out_by_amount", name="cash_out")
async def cash_out(
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
    if player_id and (is_user_admin(user.id, game.team_id, db) or user.id == game.owner_id or user.id == game.book_keeper_id):
        target_player = db.query(User).filter(User.id == player_id).first()
        if not target_player:
            raise HTTPException(status_code=404, detail="Player not found")

    return templates.TemplateResponse(
        "game/cash_out_by_amount.html",
        context={
            "request": request,
            "game_id": game.id,
            "target_player": target_player,
            "user": user,
        },
    )


def read_chips_from_form(form_data, expected_chip_ids):
    chip_values = []
    print("expected chip id", expected_chip_ids)
    for key, value in form_data.items():
        if not key.startswith("chip_"):
            continue
        chip_id = key.split("_")[1]

        try:
            chip_value_int = int(value)
        except ValueError:
            raise ValueError(f"Value '{value}' for key '{key}' is not an integer.")

        try:
            chip_id_int = int(chip_id)
        except ValueError:
            raise ValueError(f"Value '{chip_id}' for key '{key}' is not an integer.")

        if chip_id_int not in expected_chip_ids:
            raise ValueError(f"Chip ID '{chip_id}' is not in the expected list.")
        chip_values.append(ChipAmountCreate(chip_id=chip_id_int, amount=chip_value_int))

    if len(chip_values) != len(expected_chip_ids):
        raise ValueError(
            f"Expected {expected_chip_ids} chip values, but got {len(chip_values)}."
        )

    return chip_values


@router.post("/{game_id}/cash_out", name="cash_out")
async def cash_out(
    request: Request,
    game_id: int,
    player_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    errors = []

    game = get_game_by_id(game_id, db)
    if game is None:
        errors.append("Game doesn't exist anymore. Maybe it was deleted.")
        return RedirectResponse(url="/")

    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    target_player = user
    auto_approve = False
    if player_id and (is_user_admin(user.id, game.team_id, db) or user.id == game.owner_id or user.id == game.book_keeper_id):
        target_player = db.query(User).filter(User.id == player_id).first()
        if not target_player:
            raise HTTPException(status_code=404, detail="Player not found")
        auto_approve = True

    form = await request.form()
    try:
        chips = get_chips_from_structure(game.chip_structure_id, db)
        print("chips", chips)
        chip_values = read_chips_from_form(
            form, expected_chip_ids=[chip.id for chip in chips]
        )
        cash_out_form = CashOutRequest(
            amount=form.get("totalValue", 0), chips_amounts=chip_values
        )
        amount = cash_out_form.amount
        chip_amounts = cash_out_form.chips_amounts

        cashout = create_cash_out_request(game, amount, chip_amounts, db, target_player)
        if auto_approve:
            update_cash_out_status(cashout, PlayerRequestStatus.APPROVED, db, user)
            
        # Redirect to the game page
        return RedirectResponse(url=f"/game/{game.id}", status_code=303)

    except IntegrityError:
        errors.append(
            "A database error occurred (e.g., integrity constraint violation)."
        )
    except Exception as e:
        errors.append(f"An unexpected error occurred: {e}")
    except ValidationError as e:
        errors.extend([err["msg"] for err in e.errors()])
    except PydanticCustomError as e:
        errors.append(e.message)

    # Re-render template with submitted data and errors
    return templates.TemplateResponse(
        f"game/cash_out.html",
        {
            "request": request,
            "errors": errors,
            "game": game,
            "form": form,
        },
    )

    # Re-render template with submitted data and errors
    return templates.TemplateResponse(
        f"game/cash_out.html",
        {
            "request": request,
            "errors": errors,
            "game": game,
            "form": cash_out_form,
        },
    )


@router.post("/{game_id}/cash_out_by_amount", name="cash_out_by_amount")
async def cash_out_by_amount(
    request: Request,
    game_id: int,
    player_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    form = await request.form()
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    target_player = user
    auto_approve = False
    if player_id and (is_user_admin(user.id, game.team_id, db) or user.id == game.owner_id or user.id == game.book_keeper_id):
        target_player = db.query(User).filter(User.id == player_id).first()
        if not target_player:
            raise HTTPException(status_code=404, detail="Player not found")
        auto_approve = True

    errors = []

    try:
        cash_out_form = CashOutByAmountRequest(**form)
        cashout = create_cash_out_request(game, cash_out_form.amount, [], db, target_player)
        if auto_approve:
            update_cash_out_status(cashout, PlayerRequestStatus.APPROVED, db, user)
            
        return RedirectResponse(url=f"/game/{game.id}", status_code=303)
    except ValidationError as e:
        print("catching error")
        errors.extend([err["msg"] for err in e.errors()])
    except PydanticCustomError as e:
        print("catching error")
        errors.append(e.message)
    except IntegrityError:
        errors.append(
            "A database error occurred (e.g., integrity constraint violation)."
        )
    except Exception as e:
        errors.append(f"An unexpected error occurred: {e}")

    # Re-render template with submitted data and errors
    return templates.TemplateResponse(
        f"game/cash_out_by_amount.html",
        {
            "request": request,
            "errors": errors,
            "game": game,
            "form": form,
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

    if not (is_user_admin(user.id, game.team_id, db) or user.id == game.owner_id or user.id == game.book_keeper_id):
        raise HTTPException(status_code=403, detail="Only admins, the game owner, or the bookkeeper can approve cash-outs")
    action = (
        PlayerRequestStatus.APPROVED
        if action == "approve"
        else PlayerRequestStatus.DECLINED
    )
    cash_out = get_cash_out_by_id(cash_out_id, db)
    update_cash_out_status(cash_out, action, db, user)

    return RedirectResponse(url=f"/game/{game.id}", status_code=303)


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
