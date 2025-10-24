from typing import List, Type

from sqlalchemy.orm import Session

from backend.db.models.game import Game
from backend.db.repository.user import create_new_user
from backend.schemas.games import GameCreate
from backend.schemas.users import UserCreate


def create_new_game_db(game: GameCreate, db: Session):
    new_game = Game(
        owner_id=new_user.id,
        **game.dict(),
        descriptor=f"{game.default_buy_in}.{game.city}.{game.address}",
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
