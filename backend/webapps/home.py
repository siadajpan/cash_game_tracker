from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from backend.apis.v1.route_login import (
    get_current_user_from_token,
)
from backend.core.config import TEMPLATES_DIR
from backend.db.models.user import User
from backend.db.session import get_db
from backend.db.repository.game import get_running_games_for_user

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(
    request: Request,
    user: Optional[User] = Depends(get_current_user_from_token),
    msg: str = None,
    error: str = None,
    join_code: str = None,
    db: Session = Depends(get_db),
):
    if user:
        running_games = get_running_games_for_user(user, db)
    else:
        # Actually home redirects to welcome if no user normally, but let's handle None
        running_games = []

    return templates.TemplateResponse(
        "general_pages/homepage.html",
        {
            "request": request,
            "msg": msg,
            "error": error,
            "join_code": join_code,
            "user": user,
            "running_games": running_games,
        },
    )
@router.get("/my_group")
async def my_group(
    request: Request,
    sort: str = "games_count",
    order: str = "desc",
    year: str = None,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    from backend.db.models.user_game import UserGame
    from backend.db.models.game import Game
    from collections import defaultdict
    from backend.db.models.buy_in import BuyIn
    from backend.db.models.add_on import AddOn
    from backend.db.models.cash_out import CashOut
    from backend.db.models.player_request_status import PlayerRequestStatus
    from sqlalchemy import func

    # 1. Identify all games current 'user' has participated in
    my_game_ids_subquery = db.query(UserGame.game_id).filter(UserGame.user_id == user.id).subquery()
    
    # 2. Identify all people (friends) who were in those games
    friend_ids_subquery = db.query(UserGame.user_id).filter(UserGame.game_id.in_(my_game_ids_subquery)).distinct().subquery()
    friend_ids = [uid for (uid,) in db.query(UserGame.user_id).filter(UserGame.game_id.in_(my_game_ids_subquery)).distinct().all()]

    # 3. All games hosted by those people (The Universe)
    group_games = db.query(Game).filter(Game.owner_id.in_(friend_ids_subquery)).all()
    group_game_ids = [g.id for g in group_games]

    # Meta-data: Available years (based on group's games)
    all_years = set()
    for g in group_games:
        if g.date:
            all_years.add(int(str(g.date)[:4]))
    available_years = sorted(list(all_years), reverse=True)

    target_year = None
    if year and year != "all":
        try:
            target_year = int(year)
        except:
            pass

    # 4. Filter logic: We need to find the stats for each friend.
    # UserGame records for these people.
    q_friends_games = db.query(UserGame.user_id, UserGame.game_id).filter(UserGame.user_id.in_(friend_ids))
    
    current_universe_game_ids = group_game_ids
    if target_year:
        current_universe_game_ids = [g.id for g in group_games if g.date and int(str(g.date)[:4]) == target_year]
        q_friends_games = q_friends_games.filter(UserGame.game_id.in_(current_universe_game_ids))

    friends_participations = q_friends_games.all()

    # Calculate general group stats based on the universe
    stats = type("Stats", (object,), {"avg_players": 0.0, "frequency": 0})()
    
    universe_games_filtered = [g for g in group_games if not target_year or (g.date and int(str(g.date)[:4]) == target_year)]
    universe_game_ids_filtered = [g.id for g in universe_games_filtered]

    if universe_game_ids_filtered:
        total_p = db.query(func.count(UserGame.user_id)).filter(UserGame.game_id.in_(universe_game_ids_filtered)).scalar() or 0
        stats.avg_players = total_p / len(universe_game_ids_filtered)
        dates = []
        for g in universe_games_filtered:
            if g.date:
                if isinstance(g.date, str):
                    from datetime import datetime
                    try:
                        dates.append(datetime.strptime(g.date[:10], "%Y-%m-%d").date())
                    except ValueError:
                        pass
                else:
                    dates.append(g.date)
        if len(dates) > 1:
            dates.sort()
            stats.frequency = max(1, (dates[-1] - dates[0]).days // len(dates))

    players_info = []

    if current_universe_game_ids:
        counts_map = defaultdict(int)
        for uid, gid in friends_participations:
            counts_map[uid] += 1
            
        money_in = defaultdict(float)
        money_out = defaultdict(float)

        bi = db.query(BuyIn.user_id, func.sum(BuyIn.amount)).filter(BuyIn.game_id.in_(current_universe_game_ids)).group_by(BuyIn.user_id).all()
        for u_id, amt in bi:
            if u_id in friend_ids: money_in[u_id] += amt

        ao = db.query(AddOn.user_id, func.sum(AddOn.amount)).filter(AddOn.game_id.in_(current_universe_game_ids), AddOn.status == PlayerRequestStatus.APPROVED).group_by(AddOn.user_id).all()
        for u_id, amt in ao:
            if u_id in friend_ids: money_in[u_id] += amt

        co = db.query(CashOut.user_id, func.sum(CashOut.amount)).filter(CashOut.game_id.in_(current_universe_game_ids)).group_by(CashOut.user_id).all()
        for u_id, amt in co:
            if u_id in friend_ids: money_out[u_id] += amt

        users = db.query(User).filter(User.id.in_(friend_ids)).all()

        for u in users:
            b = money_out[u.id] - money_in[u.id]
            players_info.append({
                "player": u,
                "games_count": counts_map[u.id],
                "total_balance": b,
                "player_role": "ADMIN" if u.id == user.id else "MEMBER"
            })

    reverse_order = order == "desc"
    if sort == "player":
        players_info.sort(key=lambda x: x["player"].nick.lower(), reverse=reverse_order)
    elif sort == "games_count":
        players_info.sort(key=lambda x: x["games_count"], reverse=reverse_order)
    elif sort == "balance":
        players_info.sort(key=lambda x: x["total_balance"], reverse=reverse_order)
    else:
        players_info.sort(key=lambda x: x["games_count"], reverse=True)

    class FakeTeam:
        id = 0
        name = "My Group"
        search_code = ""

    return templates.TemplateResponse(
        "team/team_view.html",
        {
            "request": request,
            "user": user,
            "current_user": user,
            "is_admin": False,
            "team": FakeTeam(),
            "join_requests": [],
            "players_info": players_info,
            "sort_by": sort,
            "order": order,
            "available_years": available_years,
            "selected_year": year if year else "all",
            "stats": stats,
            "is_global_group": True,
        },
    )


@router.get("/terms-of-service/")
async def terms_of_service(request: Request):
    return templates.TemplateResponse(
        "general_pages/terms_of_service.html", {"request": request}
    )


@router.get("/privacy-policy/")
async def privacy_policy(request: Request):
    return templates.TemplateResponse(
        "general_pages/privacy_policy.html", {"request": request}
    )
