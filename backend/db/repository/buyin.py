from requests import Session
from sqlalchemy import func

from backend.db.models.buy_in import BuyIn
from backend.db.models.game import Game
from backend.db.models.user import User


def get_player_game_buy_in(user: User, game: Game, db: Session) -> float:
    """
    Return the total buy-in amount a user has in a specific game.
    """
    total_buy_in = (
        db.query(func.sum(BuyIn.amount))
        .filter(BuyIn.user_id == user.id, BuyIn.game_id == game.id)
        .scalar()
    )
    return total_buy_in or 0.0
