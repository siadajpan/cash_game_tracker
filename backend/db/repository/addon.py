from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.models.add_on import AddOn
from backend.db.models.game import Game
from backend.db.models.user import User


def get_player_game_addons(user: User, game: Game, db: Session) -> float:
    """
    Return the total addon amount a user has in a specific game.
    """
    total_addons = (
        db.query(func.sum(AddOn.amount))
        .filter(AddOn.user_id == user.id, AddOn.game_id == game.id)
        .scalar()
    )
    return total_addons or 0.0
