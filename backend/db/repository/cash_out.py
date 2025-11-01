from datetime import datetime
from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.add_on import PlayerRequestStatus
from backend.db.models.cash_out import CashOut
from backend.db.models.game import Game
from backend.db.models.user import User


def get_player_game_cash_out(user: User, game: Game, db: Session) -> List[CashOut]:
    cash_outs = (
        db.query(CashOut)
        .filter(CashOut.user_id == user.id, CashOut.game_id == game.id)
        .all()
    )
    return cash_outs


def create_cash_out_request(
    game: Game,
    amount: float,
    db: Session,
    user: User = Depends(get_current_user_from_token),
):
    """
    Create a new AddOn request for the given user and game.
    The new request starts with status = REQUESTED.
    """
    new_cash_out = CashOut(
        user_id=user.id,
        game_id=game.id,
        time=datetime.now().isoformat(),
        amount=amount,
        status=PlayerRequestStatus.REQUESTED,
    )

    db.add(new_cash_out)
    db.commit()
    db.refresh(new_cash_out)

    return new_cash_out


def get_cash_out_by_id(cash_out_id: int, db: Session) -> CashOut | None:
    """
    Retrieve a single CashOut entry by its ID.
    Returns None if the add-on does not exist.
    """
    return db.query(CashOut).filter(CashOut.id == cash_out_id).first()


def update_cash_out_status(
    cash_out: CashOut,
    new_status: PlayerRequestStatus,
    db: Session,
    user: User = Depends(get_current_user_from_token),
):
    """
    Update the status of an existing AddOn request (e.g., APPROVED or DECLINED)
    and persist the change to the database.
    """
    cash_out.status = new_status
    db.add(cash_out)
    db.commit()
    db.refresh(cash_out)
    return cash_out
