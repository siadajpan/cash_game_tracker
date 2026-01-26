from sqlite3 import IntegrityError
from typing import List, Type, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.game import Game
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.user import User
from backend.db.models.user_game import UserGame
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
        **game.model_dump(),
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
    if user_in_game(user, game):
        raise IntegrityError("User is already part of the game")

    game_association = UserGame(
        user=user,
        game=game,
        status=PlayerRequestStatus.REQUESTED,  # auto approve when creating a team
    )

    user.game_associations.append(game_association)

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
    return [
        add_on
        for add_on in game.add_ons
        if add_on.status == PlayerRequestStatus.REQUESTED
    ]


def get_game_cash_out_requests(game: Game, db: Session):
    return [
        cash_out
        for cash_out in game.cash_outs
        if cash_out.status == PlayerRequestStatus.REQUESTED
    ]


def finish_the_game(user: User, game: Game, db: Session, finish_time: Optional[str] = None):
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
    
    if finish_time:
        try:
             # Expect isoformat or similar
             from datetime import datetime
             # Assuming input is like "YYYY-MM-DDTHH:MM"
             dt_obj = datetime.strptime(finish_time, "%Y-%m-%dT%H:%M")
             game.finish_time = dt_obj
        except ValueError:
            pass # ignore invalid time formats, keep default (or none)

    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def get_user_games_count(user: User, db: Session) -> int:
    return len(user.games_played)


def get_user_team_games(user: User, team_id: int, db: Session, limit: int = None) -> List[Game]:
    """
    Returns list of games the user played in for a specific team.
    """
    query = (
        db.query(Game)
        .join(UserGame)
        .filter(UserGame.user_id == user.id, Game.team_id == team_id)
        .order_by(Game.date.desc())
    )
    
    if limit:
        query = query.limit(limit)
        
    return query.all()


def get_user_team_games_count(user: User, team_id: int, db: Session) -> int:
    """
    Returns count of games the user played in for a specific team.
    """
    return (
        db.query(Game)
        .join(UserGame)
        .filter(UserGame.user_id == user.id, Game.team_id == team_id)
        .count()
    )


def get_user_total_balance(user: User, db: Session) -> float:
    total = 0.0
    for game in user.games_played:
        total += get_user_game_balance(user, game, db)
    return total


def get_user_team_balance(user: User, team_id: int, db: Session) -> float:
    """
    Returns total balance for the user in a specific team.
    """
    total = 0.0
    team_games = get_user_team_games(user, team_id, db)
    for game in team_games:
        total += get_user_game_balance(user, game, db)
    return total


def delete_game_by_id(game_id: int, db: Session) -> bool:
    """
    Deletes a game by ID. Returns True if deleted, False if not found.
    """
    game = get_game_by_id(game_id, db)
    if not game:
        return False

    db.delete(game)
    db.commit()
    return True


def get_user_past_games(user: User, db: Session, limit: int = None) -> List[Game]:
    """
    Returns list of past (not running) games for all teams the user belongs to.
    """
    team_ids = [team.id for team in user.teams]
    if not team_ids:
        return []
        
    query = (
        db.query(Game)
        .join(UserGame)
        .filter(Game.team_id.in_(team_ids))
        .filter(UserGame.user_id == user.id)
        .filter(Game.running == False)
        .order_by(Game.date.desc())
    )
    
    if limit:
        query = query.limit(limit)
        
    return query.all()


def get_user_past_games_count(user: User, db: Session) -> int:
    """
    Returns count of past (not running) games for all teams the user belongs to.
    """
    team_ids = [team.id for team in user.teams]
    if not team_ids:
        return 0
        
    return (
        db.query(Game)
        .filter(Game.team_id.in_(team_ids))
        .filter(Game.running == False)
        .count()
    )


from sqlalchemy import func
from collections import defaultdict
from typing import Dict, Any
from backend.db.models.buy_in import BuyIn
from backend.db.models.cash_out import CashOut
from backend.db.models.add_on import AddOn

def get_player_games_stats_bulk(user_id: int, team_id: int, db: Session) -> Dict[int, Dict[str, Any]]:
    """
    Returns aggregated stats for all games in a team for a specific user.
    Key: game_id
    Value: { "balance": float, "total_pot": float, "players_count": int }
    """
    stats = defaultdict(lambda: {"balance": 0.0, "total_pot": 0.0, "players_count": 0})

    # 1. Total Pot per Game (Sum of all buyins + approved addons for ALL players in team games)
    # Note: This is global for the game, not specific to user, but we filter by team games.
    # Group by game_id
    
    # BuyIns Sum (All players)
    buy_ins_pot = (
        db.query(BuyIn.game_id, func.sum(BuyIn.amount))
        .join(Game, BuyIn.game_id == Game.id)
        .filter(Game.team_id == team_id)
        .group_by(BuyIn.game_id)
        .all()
    )
    for gid, total in buy_ins_pot:
        if total:
            stats[gid]["total_pot"] += total

    # AddOns Sum (All players, Approved only)
    add_ons_pot = (
        db.query(AddOn.game_id, func.sum(AddOn.amount))
        .join(Game, AddOn.game_id == Game.id)
        .filter(Game.team_id == team_id, AddOn.status == PlayerRequestStatus.APPROVED)
        .group_by(AddOn.game_id)
        .all()
    )
    for gid, total in add_ons_pot:
        if total:
            stats[gid]["total_pot"] += total

    # 2. Players Count per Game
    players_counts = (
        db.query(UserGame.game_id, func.count(UserGame.user_id))
        .join(Game, UserGame.game_id == Game.id)
        .filter(Game.team_id == team_id)
        .group_by(UserGame.game_id)
        .all()
    )
    for gid, count in players_counts:
        stats[gid]["players_count"] = count

    # 3. User Balance per Game
    # Balance = CashOut (Approved) - (BuyIn + AddOn (Approved))
    
    money_in = defaultdict(float)
    money_out = defaultdict(float)

    # User BuyIns
    user_buy_ins = (
        db.query(BuyIn.game_id, func.sum(BuyIn.amount))
        .join(Game, BuyIn.game_id == Game.id)
        .filter(Game.team_id == team_id, BuyIn.user_id == user_id)
        .group_by(BuyIn.game_id)
        .all()
    )
    for gid, total in user_buy_ins:
        if total:
            money_in[gid] += total

    # User AddOns
    user_add_ons = (
        db.query(AddOn.game_id, func.sum(AddOn.amount))
        .join(Game, AddOn.game_id == Game.id)
        .filter(Game.team_id == team_id, AddOn.user_id == user_id, AddOn.status == PlayerRequestStatus.APPROVED)
        .group_by(AddOn.game_id)
        .all()
    )
    for gid, total in user_add_ons:
        if total:
            money_in[gid] += total

    # User CashOuts
    user_cash_outs = (
        db.query(CashOut.game_id, func.sum(CashOut.amount))
        .join(Game, CashOut.game_id == Game.id)
        .filter(Game.team_id == team_id, CashOut.user_id == user_id, CashOut.status == PlayerRequestStatus.APPROVED)
        .group_by(CashOut.game_id)
        .all()
    )
    for gid, total in user_cash_outs:
        if total:
            money_out[gid] += total

    # Combine Balance
    # Iterate known games for this user (from buyins/addons/matches)
    # Or just iterate stats keys, which cover all games in team. 
    # But wait, user might not play in ALL team games.
    # We should only calculate balance for games the user is actually IN (UserGame).
    # But money_in/money_out are strictly filtered by user_id so they are safe.
    # The stats dict has keys for ALL games in team.
    # We can just iterate the money_in/money_out keys to update balance.
    
    involved_games = set(money_in.keys()) | set(money_out.keys())
    for gid in involved_games:
        stats[gid]["balance"] = money_out[gid] - money_in[gid]

    return stats


def get_user_past_games_stats_bulk(user_id: int, game_ids: List[int], db: Session) -> Dict[int, Dict[str, Any]]:
    """
    Returns aggregated stats for a specific list of games (past games view).
    Key: game_id
    Value: { "my_balance": float, "total_pot": float, "players_count": int }
    """
    stats = defaultdict(lambda: {"my_balance": 0.0, "total_pot": 0.0, "players_count": 0})
    if not game_ids:
        return stats

    # 1. Total Pot per Game
    buy_ins_pot = (
        db.query(BuyIn.game_id, func.sum(BuyIn.amount))
        .filter(BuyIn.game_id.in_(game_ids))
        .group_by(BuyIn.game_id)
        .all()
    )
    for gid, total in buy_ins_pot:
        if total: stats[gid]["total_pot"] += total

    add_ons_pot = (
        db.query(AddOn.game_id, func.sum(AddOn.amount))
        .filter(AddOn.game_id.in_(game_ids), AddOn.status == PlayerRequestStatus.APPROVED)
        .group_by(AddOn.game_id)
        .all()
    )
    for gid, total in add_ons_pot:
        if total: stats[gid]["total_pot"] += total

    # 2. Players Count
    players_counts = (
        db.query(UserGame.game_id, func.count(UserGame.user_id))
        .filter(UserGame.game_id.in_(game_ids))
        .group_by(UserGame.game_id)
        .all()
    )
    for gid, count in players_counts:
        stats[gid]["players_count"] = count

    # 3. My Balance
    money_in = defaultdict(float)
    money_out = defaultdict(float)

    user_buy_ins = (
        db.query(BuyIn.game_id, func.sum(BuyIn.amount))
        .filter(BuyIn.game_id.in_(game_ids), BuyIn.user_id == user_id)
        .group_by(BuyIn.game_id)
        .all()
    )
    for gid, total in user_buy_ins:
        if total: money_in[gid] += total

    user_add_ons = (
        db.query(AddOn.game_id, func.sum(AddOn.amount))
        .filter(AddOn.game_id.in_(game_ids), AddOn.user_id == user_id, AddOn.status == PlayerRequestStatus.APPROVED)
        .group_by(AddOn.game_id)
        .all()
    )
    for gid, total in user_add_ons:
        if total: money_in[gid] += total

    user_cash_outs = (
        db.query(CashOut.game_id, func.sum(CashOut.amount))
        .filter(CashOut.game_id.in_(game_ids), CashOut.user_id == user_id, CashOut.status == PlayerRequestStatus.APPROVED)
        .group_by(CashOut.game_id)
        .all()
    )
    for gid, total in user_cash_outs:
        if total: money_out[gid] += total

    for gid in game_ids:
        # Defaults to 0 if not in dict
        stats[gid]["my_balance"] = money_out[gid] - money_in[gid]

    return stats
