from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from pydantic_core import PydanticCustomError, ValidationError
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

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
    get_chip_structure,
    get_chip_structure_as_list,
)
from backend.db.repository.game import (
    get_game_by_id,
    user_in_game,
)
from backend.db.session import get_db
from backend.webapps.game.game_forms import (
    CashOutByAmountRequest,
    CashOutRequest,
)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/{game_id}/cash_out", name="cash_out")
async def cash_out(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet
    chip_structure = get_chip_structure_as_list(game.chip_structure_id, db)

    return templates.TemplateResponse(
        "game/cash_out.html",
        context={
            "request": request,
            "game_id": game.id,
            "chip_structure": chip_structure,
        },
    )


@router.get("/{game_id}/cash_out_by_amount", name="cash_out")
async def cash_out(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    return templates.TemplateResponse(
        "game/cash_out_by_amount.html",
        context={
            "request": request,
            "game_id": game.id,
        },
    )

def read_chip_values(form, chip_structure):
    chip_values = []
    for chip in chip_structure:
        chip_values.append(ChipAmountCreate(chip_id=chip['id'], amount=int(form.get(f"chip_{chip['id']}", 0))))
    return chip_values

@router.post("/{game_id}/cash_out", name="cash_out")
async def cash_out(
    request: Request,
    game_id: int,
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
    form = await request.form()
    chip_structure = get_chip_structure_as_list(game.chip_structure_id, db)
    chip_values = read_chip_values(form, chip_structure)
    try:
        cash_out_form = CashOutRequest(amount=form.get("totalValue", 0), chips_amounts=chip_values)
        print ("form",cash_out_form)
        amount = cash_out_form.amount
        chip_amounts = cash_out_form.chips_amounts

        create_cash_out_request(game, amount, chip_amounts, db, user)
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
            "form": cash_out_form,
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    form = await request.form()
    game = get_game_by_id(game_id, db)
    if not user_in_game(user, game):
        return RedirectResponse(url=f"/{game.id}/join")  # not in the game yet

    errors = []

    try:
        cash_out_form = CashOutByAmountRequest(**form)
        create_cash_out_request(game, cash_out_form.amount, [], db, user)
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

    # TODO check if current user is game owner
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
