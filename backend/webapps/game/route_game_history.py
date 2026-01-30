from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, Response

from backend.db.session import get_db
from backend.core.config import TEMPLATES_DIR
from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.user import User
from backend.db.models.game import Game
from backend.db.models.buy_in import BuyIn
from backend.db.models.add_on import AddOn
from backend.db.models.cash_out import CashOut
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.repository.game import get_game_by_id
from backend.db.repository.team import is_user_admin

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)

def verify_book_keeper_access(game_id: int, user_id: int, db: Session) -> Game:
    game = get_game_by_id(game_id, db)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if user is the assigned book keeper OR the team admin
    is_admin = is_user_admin(user_id, game.team_id, db)
    is_assigned = (game.book_keeper_id == user_id)
    is_owner = (game.owner_id == user_id)
    
    if not (is_admin or is_assigned or is_owner):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return game

@router.get("/{game_id}/player/{player_id}/history", name="player_game_history")
async def player_game_history(
    request: Request,
    game_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    # Public access to view history
    game = get_game_by_id(game_id, db)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    target_player = db.query(User).filter(User.id == player_id).first()
    if not target_player:
        return Response("Player not found", status_code=404)

    is_admin = is_user_admin(user.id, game.team_id, db)
    can_edit = is_admin or (game.book_keeper_id == user.id) or (game.owner_id == user.id)

    # Fetch all events
    buy_ins = db.query(BuyIn).filter(BuyIn.game_id == game_id, BuyIn.user_id == player_id).all()
    add_ons = db.query(AddOn).filter(AddOn.game_id == game_id, AddOn.user_id == player_id).all()
    cash_outs = db.query(CashOut).filter(CashOut.game_id == game_id, CashOut.user_id == player_id).all()

    # Combine and sort by time (assuming ISO format strings)
    events = []
    for bi in buy_ins:
        events.append({"type": "buy_in", "obj": bi, "time": bi.time, "amount": bi.amount, "id": bi.id})
    for ao in add_ons:
        if ao.status == "APPROVED":
            events.append({"type": "add_on", "obj": ao, "time": ao.time, "amount": ao.amount, "id": ao.id, "status": ao.status})
    for co in cash_outs:
        if co.status == "APPROVED":
            events.append({"type": "cash_out", "obj": co, "time": co.time, "amount": co.amount, "id": co.id, "status": co.status})

    events.sort(key=lambda x: x["time"] or "")


    return templates.TemplateResponse(
        "game/player_history_full.html",
        {
            "request": request,
            "game": game,
            "player": target_player,
            "events": events,
            "user": user,
            "can_edit": can_edit,
            "total_money_in": sum(bi.amount for bi in buy_ins) + sum(ao.amount for ao in add_ons if ao.status == "APPROVED"),
            "total_money_out": sum(co.amount for co in cash_outs if co.status == "APPROVED")
        },
    )

# --- Buy In ---

@router.post("/{game_id}/buy_in/add", name="add_buy_in_manual")
async def add_buy_in_manual(
    game_id: int,
    player_id: int = Form(...),
    amount: float = Form(...),
    time: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = verify_book_keeper_access(game_id, user.id, db)
    
    if not time:
        time = datetime.now().isoformat()

    new_bi = BuyIn(
        user_id=player_id,
        game_id=game_id,
        amount=amount,
        time=time
    )
    db.add(new_bi)
    db.commit()
    
    return Response(status_code=200, headers={"HX-Trigger": "refreshHistory, refreshTable"})


def get_event_by_type_and_id(game_id: int, event_type: str, event_id: int, db: Session):
    if event_type == "buy_in":
        return db.query(BuyIn).filter(BuyIn.id == event_id, BuyIn.game_id == game_id).first()
    elif event_type == "add_on":
        return db.query(AddOn).filter(AddOn.id == event_id, AddOn.game_id == game_id).first()
    elif event_type == "cash_out":
        return db.query(CashOut).filter(CashOut.id == event_id, CashOut.game_id == game_id).first()
    return None

def render_history_row(request: Request, game: Game, event_obj, event_type: str, user: User, db: Session, edit_mode: bool = False):
    event_data = {
        "type": event_type,
        "obj": event_obj,
        "time": event_obj.time,
        "amount": event_obj.amount,
        "id": event_obj.id,
        "status": getattr(event_obj, "status", None)
    }
    
    template_name = "game/partials/history_row_edit.html" if edit_mode else "game/partials/history_row.html"
    is_admin = is_user_admin(user.id, game.team_id, db)
    can_edit = is_admin or (game.book_keeper_id == user.id) or (game.owner_id == user.id)

    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "game": game,
            "event": event_data,
            "can_edit": can_edit
        }
    )

@router.get("/{game_id}/{event_type}/{event_id}/row", name="get_history_row")
async def get_history_row(
    request: Request,
    game_id: int,
    event_type: str,
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = get_game_by_id(game_id, db)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
        
    event_obj = get_event_by_type_and_id(game_id, event_type, event_id, db)
    if not event_obj:
        return Response(status_code=404)

    return render_history_row(request, game, event_obj, event_type, user, db, edit_mode=False)

@router.get("/{game_id}/{event_type}/{event_id}/edit_row", name="get_history_row_edit")
async def get_history_row_edit(
    request: Request,
    game_id: int,
    event_type: str,
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    # Permission check for editing UI
    game = verify_book_keeper_access(game_id, user.id, db)
    
    event_obj = get_event_by_type_and_id(game_id, event_type, event_id, db)
    if not event_obj:
        return Response(status_code=404)

    return render_history_row(request, game, event_obj, event_type, user, db, edit_mode=True)


@router.put("/{game_id}/{event_type}/{event_id}", name="update_event_generic")
async def update_event_generic(
    request: Request,
    game_id: int,
    event_type: str,
    event_id: int,
    amount: float = Form(...),
    time: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    game = verify_book_keeper_access(game_id, user.id, db)
    
    event_obj = get_event_by_type_and_id(game_id, event_type, event_id, db)
    if event_obj:
        event_obj.amount = amount
        event_obj.time = time
        db.commit()
    
    # Return the read-only row
    return render_history_row(request, game, event_obj, event_type, user, db, edit_mode=False)


@router.delete("/{game_id}/{event_type}/{event_id}", name="delete_event_generic")
async def delete_event_generic(
    game_id: int,
    event_type: str,
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    verify_book_keeper_access(game_id, user.id, db)
    
    event_obj = get_event_by_type_and_id(game_id, event_type, event_id, db)
    if event_obj:
        db.delete(event_obj)
        db.commit()
    
    return Response(status_code=200) # Returns empty response to remove element from DOM

