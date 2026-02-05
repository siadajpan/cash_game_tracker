from collections import defaultdict
from multiprocessing import Value
from select import select
from sqlite3 import IntegrityError
from typing import Dict, List, Type, Optional
import random

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.apis.v1.route_login import get_current_user
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.team import Team
from backend.db.models.user import User
from backend.db.models.game import Game
from backend.db.models.user_team import UserTeam
from backend.db.repository.user import create_new_user
from backend.schemas.team import TeamCreate


def create_new_team(team: TeamCreate, creator: User, db: Session) -> Team:
    """
    Creates a new team with the given creator as an admin and player.

    Args:
        team: TeamCreate schema object with team info.
        creator: User instance who creates the team.
        db: SQLAlchemy session.

    Returns:
        The newly created Team instance.
    """
    new_team = Team(**team.model_dump())

    from backend.db.models.team_role import TeamRole

    team_association = UserTeam(
        user=creator,
        team=new_team,
        status=PlayerRequestStatus.APPROVED,  # auto approve when creating a team
        role=TeamRole.ADMIN,
    )

    creator.team_associations.append(team_association)

    # 3. Persist
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return new_team


def join_team(team_model: Team, user, db: Session) -> Team:
    """
    Adds an existing User to an existing Team's list of members
    by leveraging the many-to-many relationship defined in the models.

    Args:
        team_model: The SQLAlchemy Team model instance to join.
        user: The SQLAlchemy User model instance to be added to the team.
        db: SQLAlchemy session.

    Returns:
        The updated Team model instance.
    """
    team_association = UserTeam(
        user=user,
        team=team_model,
        status=PlayerRequestStatus.APPROVED,  # team owner needs to approve it
    )

    user.team_associations.append(team_association)
    db.commit()
    db.refresh(team_model)

    return team_model


def remove_user_from_team(team: Team, user: User, db: Session):
    """
    Removes a user from a team and removes their history (games, buyins) from that team's games.
    """
    from backend.db.models.user_game import UserGame
    from backend.db.models.buy_in import BuyIn
    from backend.db.models.add_on import AddOn
    from backend.db.models.cash_out import CashOut
    from backend.db.models.game import Game

    # 1. Remove UserTeam association (Member of team)
    association = (
        db.query(UserTeam)
        .filter(UserTeam.team_id == team.id, UserTeam.user_id == user.id)
        .one_or_none()
    )
    if association:
        db.delete(association)

    # 2. Get IDs of games belonging to this team
    # (We can do bulk delete with WHERE IN subquery or similar)
    team_game_ids = db.query(Game.id).filter(Game.team_id == team.id)

    # 3. Remove UserGame associations (Player in specific games)
    db.query(UserGame).filter(
        UserGame.user_id == user.id, UserGame.game_id.in_(team_game_ids)
    ).delete(synchronize_session=False)

    # 4. Remove Financials (BuyIn, AddOn, CashOut)
    db.query(BuyIn).filter(
        BuyIn.user_id == user.id, BuyIn.game_id.in_(team_game_ids)
    ).delete(synchronize_session=False)

    db.query(AddOn).filter(
        AddOn.user_id == user.id, AddOn.game_id.in_(team_game_ids)
    ).delete(synchronize_session=False)

    db.query(CashOut).filter(
        CashOut.user_id == user.id, CashOut.game_id.in_(team_game_ids)
    ).delete(synchronize_session=False)

    db.commit()


def get_team_by_name(team_name, db: Session):
    return db.query(Team).filter(Team.name == team_name).one_or_none()


def check_team_exists(team_name: str, db: Session) -> bool:
    """
    Check if a team with the given name exists in the database.

    Args:
        team_name: Name of the team to check.
        db: SQLAlchemy session.

    Returns:
        True if the team exists, False otherwise.
    """
    team = db.query(Team).filter(Team.name == team_name).one_or_none()
    return team is not None


def get_team_users(team: Team, db: Session) -> List[User]:
    """
    Retrieve all users (players) in a given team.

    Args:
        team: Team instance
        db: SQLAlchemy session

    Returns:
        List of User instances who are members of the team
    """
    # Option 1: Access the relationship directly (lazy-loaded)
    return team.users

    # Option 2: Query explicitly from the User table
    # return db.query(User).join(User.teams).filter(Team.id == team.id).all()


def get_team_by_id(team_id: int, db: Session) -> Optional[Team]:
    """
    Fetches a Team model instance by its ID.
    """
    return db.query(Team).filter(Team.id == team_id).one_or_none()


def is_user_admin(user_id: int, team_id: int, db: Session) -> bool:
    """
    Checks if a user has the ADMIN role in a team.
    """
    from backend.db.models.team_role import TeamRole

    assoc = (
        db.query(UserTeam)
        .filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id)
        .one_or_none()
    )
    return assoc is not None and assoc.role == TeamRole.ADMIN


def is_user_privileged_for_team(user_id: int, team_id: int, db: Session) -> bool:
    """
    Checks if a user is an ADMIN of the team OR is a Book Keeper for any active game in the team.
    """
    if is_user_admin(user_id, team_id, db):
        return True

    from backend.db.models.game import Game
    
    active_games_as_book_keeper = db.query(Game).filter(
        Game.team_id == team_id,
        Game.book_keeper_id == user_id,
        Game.finish_time == None
    ).count()
    
    return active_games_as_book_keeper > 0





def update_user_role(team_id: int, user_id: int, role: str, db: Session):
    """
    Updates the role of a user in a team.
    """
    from backend.db.models.team_role import TeamRole

    assoc = (
        db.query(UserTeam)
        .filter(UserTeam.user_id == user_id, UserTeam.team_id == team_id)
        .one_or_none()
    )
    if assoc:
        assoc.role = TeamRole(role)
        db.add(assoc)
        db.commit()



def get_team_join_requests(team: Team, db: Session) -> List[UserTeam]:
    """
    Retrieves a list of UserTeam objects who have requested to join the specified team.
    """
    return (
        db.query(UserTeam)
        .filter(
            UserTeam.team_id == team.id,
            UserTeam.status == PlayerRequestStatus.REQUESTED,
        )
        .all()
    )


def get_team_approved_players(team: Team, db: Session) -> List[User]:
    """
    Retrieves a list of User objects who have requested to join the specified team.
    """
    return (
        db.query(User)
        .join(UserTeam)
        .filter(
            UserTeam.team_id == team.id,
            UserTeam.status == PlayerRequestStatus.APPROVED,
        )
        .all()
    )


def decide_join_team(team_id, user_id, approve: bool, db: Session):
    # 2. Find and Validate the Request
    # Locate the UserTeam entry that links the user and the team with a 'REQUESTED' status.
    request_entry = (
        db.query(UserTeam)
        .filter(
            UserTeam.team_id == team_id,
            UserTeam.user_id == user_id,
            UserTeam.status == PlayerRequestStatus.REQUESTED,
        )
        .first()
    )

    if approve:
        # 3. Update the Status
        request_entry.status = PlayerRequestStatus.APPROVED
    else:
        request_entry.status = PlayerRequestStatus.DECLINED

    # 4. Commit to Database
    db.add(request_entry)
    db.commit()


def approve_all_join_requests(team_id: int, db: Session):
    """
    Approves all pending join requests for a team.
    """
    db.query(UserTeam).filter(
        UserTeam.team_id == team_id, UserTeam.status == PlayerRequestStatus.REQUESTED
    ).update({UserTeam.status: PlayerRequestStatus.APPROVED}, synchronize_session=False)
    db.commit()


def generate_team_code(
    db: Session, min_digits: int = 4, max_digits=8, max_attempts: int = 100
) -> str:
    """
    Generate a unique numeric team code.
    Starts with 4 digits, expands if all are taken.
    """
    digits = min_digits

    for _ in range(max_digits - min_digits):
        # generate a few random codes at this digit length
        for _ in range(max_attempts):
            code_int = random.randint(0, 10**digits - 1)
            code = f"{code_int:0{digits}d}"  # zero-padded

            # Check if it exists
            exists = db.query(Team).filter_by(search_code=code).first()
            if not exists:
                return code

        # if all attempts failed, increase digit count
        digits += 1
        print(
            f"All {digits-1}-digit codes exhausted, switching to {digits}-digit codes."
        )

    raise ValueError("Can't generate the team code, try again.")


def get_team_by_search_code(search_code: str, db: Session) -> Optional[Team]:
    """
    Fetches a Team model instance by its ID.
    """
    return db.query(Team).filter(Team.search_code == search_code).one_or_none()


def get_user(doctor_id, db):
    return db.get(User, doctor_id)


def list_all_users(db):
    users = db.query(User).all()

    return users


def delete_team(team: Team, db: Session):
    """
    Deletes a team and all its associated data (games, user mappings) via cascade.
    """
    db.delete(team)
    db.commit()


from sqlalchemy import func
from backend.db.models.buy_in import BuyIn
from backend.db.models.cash_out import CashOut
from backend.db.models.add_on import AddOn
from backend.db.models.user_game import UserGame


def get_team_player_stats_bulk(
    team_id: int, db: Session, year: int = None
) -> Dict[int, Dict]:
    """
    Returns a dictionary mapping user_id to their stats in the team:
    {
        user_id: {
            "games_count": int,
            "total_balance": float
        }
    }
    Optimized to use aggregation queries instead of N+1 loops.
    """
    stats = defaultdict(lambda: {"games_count": 0, "total_balance": 0.0})

    # 1. Games Count
    q1 = (
        db.query(UserGame.user_id, func.count(UserGame.game_id))
        .join(Game, UserGame.game_id == Game.id)
        .filter(Game.team_id == team_id)
    )
    if year:
        q1 = q1.filter(Game.date.like(f"{year}%"))
    games_counts = q1.group_by(UserGame.user_id).all()

    for uid, count in games_counts:
        stats[uid]["games_count"] = count

    # 2. Buy Ins Sum
    q2 = (
        db.query(BuyIn.user_id, func.sum(BuyIn.amount))
        .join(Game, BuyIn.game_id == Game.id)
        .filter(Game.team_id == team_id)
    )
    if year:
        q2 = q2.filter(Game.date.like(f"{year}%"))
    buy_ins = q2.group_by(BuyIn.user_id).all()

    money_in = defaultdict(float)
    for uid, total in buy_ins:
        if total:
            money_in[uid] += total

    # 3. Add Ons Sum (Approved only)
    q3 = (
        db.query(AddOn.user_id, func.sum(AddOn.amount))
        .join(Game, AddOn.game_id == Game.id)
        .filter(Game.team_id == team_id, AddOn.status == PlayerRequestStatus.APPROVED)
    )
    if year:
        q3 = q3.filter(Game.date.like(f"{year}%"))
    add_ons = q3.group_by(AddOn.user_id).all()

    for uid, total in add_ons:
        if total:
            money_in[uid] += total

    # 4. Cash Outs Sum (Approved only)
    q4 = (
        db.query(CashOut.user_id, func.sum(CashOut.amount))
        .join(Game, CashOut.game_id == Game.id)
        .filter(Game.team_id == team_id, CashOut.status == PlayerRequestStatus.APPROVED)
    )
    if year:
        q4 = q4.filter(Game.date.like(f"{year}%"))
    cash_outs = q4.group_by(CashOut.user_id).all()

    money_out = defaultdict(float)
    for uid, total in cash_outs:
        if total:
            money_out[uid] += total

    # Calculate Balance
    # We iterate over all keys found in any result to ensure coverage
    all_users = set(stats.keys()) | set(money_in.keys()) | set(money_out.keys())

    for uid in all_users:
        stats[uid]["total_balance"] = money_out[uid] - money_in[uid]
        stats[uid]["total_investment"] = money_in[uid]

    return stats
