from typing import List, Type, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.game import Game
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.user import User
from backend.db.repository.add_on import get_player_game_addons
from backend.db.repository.buy_in import get_player_game_buy_ins
from backend.db.repository.cash_out import get_player_game_cash_out
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


def get_user_game_balance(player: User, game: Game, db: Session) -> float:
    buy_ins = get_player_game_buy_ins(player, game, db)
    add_ons = get_player_game_addons(player, game, db)
    cash_outs = get_player_game_cash_out(player, game, db)

    buy_in_sum = sum([bi.amount for bi in buy_ins])
    add_on_sum = sum(
        [ao.amount for ao in add_ons if ao.status == PlayerRequestStatus.APPROVED]
    )
    money_in = buy_in_sum + add_on_sum
    cash_out = sum(
        [co.amount for co in cash_outs if co.status == PlayerRequestStatus.APPROVED]
    )
    balance = cash_out - money_in
    return balance


def get_game_add_on_requests(game: Game, db: Session):
    return [add_on for add_on in game.add_ons if add_on.status == PlayerRequestStatus.REQUESTED]

def get_game_cash_out_requests(game: Game, db: Session):
    return [cash_out for cash_out in game.cash_outs if cash_out.status == PlayerRequestStatus.REQUESTED]

def finish_the_game(user: User, game: Game, db: Session):
    """
    Mark a game as finished (running = False). Only the owner can finish the game.
    """
    if game.owner_id != user.id:
        raise PermissionError("Only the owner can finish the game.")

    add_ons = get_game_add_on_requests(game, db)
    cash_outs = get_game_cash_out_requests(game, db)
    for request in add_ons + cash_outs:
        request.status = PlayerRequestStatus.DECLINED
        db.add(request)
        
    game.running = False
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def get_user_games_count(user: User, db: Session) -> int:
    return len(user.games_played)


def get_user_total_balance(user: User, db: Session) -> float:
    total = 0.0
    for game in user.games_played:
        total += get_user_game_balance(user, game, db)
    return total
