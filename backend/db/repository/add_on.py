from datetime import datetime
from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.add_on import AddOn, PlayerRequestStatus
from backend.db.models.game import Game
from backend.db.models.user import User


def get_player_game_addons(user: User, game: Game, db: Session) -> List[AddOn]:
    """
    Return all AddOn objects a user has in a specific game.
    """
    addons = (
        db.query(AddOn)
        .filter(AddOn.user_id == user.id, AddOn.game_id == game.id)
        .all()
    )
    return addons


def get_player_game_total_approved_add_on_amount(user: User, game: Game, db: Session) -> float:
    """
    Return the total buy-in amount a user has in a specific game.
    """
    total_add_pm = (
        db.query(func.sum(AddOn.amount))
        .filter(AddOn.user_id == user.id, AddOn.game_id == game.id, AddOn.status == PlayerRequestStatus.APPROVED)
        .scalar()
    )
    return total_add_pm or 0.0

def create_add_on_request(game: Game, amount: float, db: Session,
                                                       user: User = Depends(get_current_user_from_token),
                          ):
    """
    Create a new AddOn request for the given user and game.
    The new request starts with status = REQUESTED.
    """
    new_addon = AddOn(
        user_id=user.id,
        game_id=game.id,
        time=datetime.now().isoformat(),
        amount=amount,
        status=PlayerRequestStatus.REQUESTED
    )

    db.add(new_addon)
    db.commit()
    db.refresh(new_addon)

    return new_addon

def get_add_on_by_id(add_on_id: int, db: Session) -> AddOn | None:
    """
    Retrieve a single AddOn entry by its ID.
    Returns None if the add-on does not exist.
    """
    return db.query(AddOn).filter(AddOn.id == add_on_id).first()

def update_add_on_status(add_on: AddOn, new_status: PlayerRequestStatus, db: Session,
                         user: User = Depends(get_current_user_from_token),
                         ):
    """
    Update the status of an existing AddOn request (e.g., APPROVED or DECLINED)
    and persist the change to the database.
    """
    add_on.status = new_status
    db.add(add_on)
    db.commit()
    db.refresh(add_on)
    return add_on