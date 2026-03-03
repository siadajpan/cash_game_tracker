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

    past_games = db.query(Game).join(UserGame).filter(UserGame.user_id == user.id).all()
    all_years = set()
    for g in past_games:
        if g.date:
            all_years.add(int(str(g.date)[:4]))
    available_years = sorted(list(all_years), reverse=True)

    target_year = None
    if year and year != "all":
        try:
            target_year = int(year)
        except:
            pass

    if target_year:
        past_games = [g for g in past_games if g.date and int(str(g.date)[:4]) == target_year]

    game_ids = [g.id for g in past_games]
    
    stats = type("Stats", (object,), {"avg_players": 0.0, "frequency": 0})()
    
    if game_ids:
        total_p = db.query(func.count(UserGame.user_id)).filter(UserGame.game_id.in_(game_ids)).scalar() or 0
        stats.avg_players = total_p / len(game_ids)
        dates = []
        for g in past_games:
            if g.date:
                # Some dates are stored as str, others as date objects. Handle strings to calculate days.
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

    if game_ids:
        counts = db.query(UserGame.user_id, func.count(UserGame.game_id)).filter(UserGame.game_id.in_(game_ids)).group_by(UserGame.user_id).all()
        counts_map = {uid: c for uid, c in counts}
        
        money_in = defaultdict(float)
        money_out = defaultdict(float)

        bi = db.query(BuyIn.user_id, func.sum(BuyIn.amount)).filter(BuyIn.game_id.in_(game_ids)).group_by(BuyIn.user_id).all()
        for u_id, amt in bi:
            if amt: money_in[u_id] += amt

        ao = db.query(AddOn.user_id, func.sum(AddOn.amount)).filter(AddOn.game_id.in_(game_ids), AddOn.status == PlayerRequestStatus.APPROVED).group_by(AddOn.user_id).all()
        for u_id, amt in ao:
            if amt: money_in[u_id] += amt

        co = db.query(CashOut.user_id, func.sum(CashOut.amount)).filter(CashOut.game_id.in_(game_ids), CashOut.status == PlayerRequestStatus.APPROVED).group_by(CashOut.user_id).all()
        for u_id, amt in co:
            if amt: money_out[u_id] += amt

        user_ids = counts_map.keys()
        users = db.query(User).filter(User.id.in_(user_ids)).all()

        for u in users:
            b = money_out[u.id] - money_in[u.id]
            # Exclude the user themself optionally? Actually, let's keep them in so they see their total balance
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
