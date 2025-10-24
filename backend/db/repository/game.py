from typing import List, Type

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.repository.user import create_new_user
from backend.db.session import get_db
from backend.schemas.games import GameCreate
from datetime import date


def create_new_game_db(game: GameCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_game = Game(
        owner_id=current_user.id,
        date=date.today(),
        **game.dict(),
    )
    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return new_game


def retrieve_game(practice_id: int, db: Session) -> Type[Game]:
    item = db.get(Game, practice_id)

    return item


def list_games(db: Session) -> List[Type[Game]]:
    practices = db.query(Game).all()

    return practices
