from typing import List, Type

from sqlalchemy.orm import Session

from backend.db.models.game import Game
from backend.db.repository.users import create_new_user
from backend.schemas.games import GameCreate
from backend.schemas.users import UserCreate


def create_new_game(practice: GameCreate, db: Session):
    new_user = create_new_user(
        UserCreate(date=practice.date, password=practice.password), db
    )

    del practice.date
    del practice.password

    new_practice = Game(
        user_id=new_user.id,
        **practice.dict(),
        descriptor=f"{practice.default_buy_in}.{practice.city}.{practice.address}",
    )
    db.add(new_practice)
    db.commit()
    db.refresh(new_practice)

    return new_practice


def retrieve_practice(practice_id: int, db: Session) -> Type[Game]:
    item = db.get(Game, practice_id)

    return item


def list_practices(db: Session) -> List[Type[Game]]:
    practices = db.query(Game).all()

    return practices
