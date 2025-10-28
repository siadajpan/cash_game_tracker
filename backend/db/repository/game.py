from typing import List, Type, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.session import get_db
from backend.schemas.games import GameCreate
from datetime import date


def create_new_game_db(
    game: GameCreate,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    new_game = Game(
        owner_id=current_user.id,
        **game.dict(),
    )
    # 2. Add the creator as a player (Many-to-Many)
    new_game.players.append(current_user)

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return new_game


def get_game_by_id(game_id: int, db: Session) -> Optional[Game]:
    return db.query(Game).filter(Game.id == game_id).one_or_none()


def list_games(db: Session) -> List[Type[Game]]:
    practices = db.query(Game).all()

    return practices


def user_in_game(user: User, game: Game):
    return user in game.players


def add_user_to_game(user: User, game: Game, db: Session) -> None:
    """
    Add a user to a game's players list if not already added.
    """
    if not user_in_game(user, game):
        game.players.append(user)
        db.add(game)  # optional, usually not needed if the game is already in session
        db.commit()
        db.refresh(game)


def finish_the_game(user: User, game: Game, db: Session):
    """
    Mark a game as finished (running = False). Only the owner can finish the game.
    """
    if game.owner_id != user.id:
        raise PermissionError("Only the owner can finish the game.")

    game.running = False
    db.add(game)
    db.commit()
    db.refresh(game)
    return game