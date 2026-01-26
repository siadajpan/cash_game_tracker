import json
from datetime import datetime
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from backend.apis.v1.route_login import get_current_user, get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.team import Team
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.models.user_team import UserTeam
from backend.db.repository.add_on import get_player_game_addons
from backend.db.repository.buy_in import get_player_game_total_buy_in_amount
from backend.db.repository.game import (
    get_user_games_count,
    get_user_total_balance,
    get_user_team_games_count,
    get_user_team_balance,
    get_user_game_balance,
    get_user_team_games,
)
from backend.db.repository.team import (
    create_new_user,
    decide_join_team,
    generate_team_code,
    get_team_approved_players,
    get_team_by_id,
    get_team_by_search_code,
    get_team_join_requests,
    get_user,
    create_new_team,
    join_team,
    get_team_by_name,
    remove_user_from_team,
)
from backend.db.session import get_db
from backend.schemas.team import TeamCreate
from backend.schemas.user import UserCreate
from backend.webapps.team.forms import TeamCreateForm, TeamJoinForm
import os
from sqlalchemy import select

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter()


@router.get("/create")
async def create_form(request: Request):
    # Provide empty defaults for form fields and errors
    context = {
        "request": request,
        "errors": [],
        "name": "",
    }
    return templates.TemplateResponse("team/create.html", context)


@router.post("/create", name="create_team")
async def create_team(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    form = await request.form()
    errors = []

    try:
        team_create_form = TeamCreateForm(**form)

        team_search_code = generate_team_code(db)
        # Use all extracted variables
        new_team_data = TeamCreate(
            **team_create_form.model_dump(), search_code=team_search_code
        )
        create_new_team(team=new_team_data, creator=current_user, db=db)
        return responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    except PydanticCustomError as e:
        errors.append(e.message())
    except IntegrityError:
        errors.append("Group with that name already exists.")

    # Re-render with all submitted data
    return templates.TemplateResponse(
        "team/create.html",
        {
            "request": request,
            "errors": errors,
            "form": form,
        },
    )


@router.get("/join")
async def join_form(request: Request):
    # Provide empty defaults for form fields and errors
    context = {
        "request": request,
        "errors": [],
        "name": "",
    }
    return templates.TemplateResponse("team/join.html", context)


@router.post("/join", name="join_team")
async def join_team_post(  # Renamed function to avoid conflict with service function
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    form = await request.form()
    # Load form data using your custom loader
    template_name = "team/join.html"
    errors = []

    try:
        form = TeamJoinForm(**form)

        search_code = form.search_code

        # 2. Find the team in the database
        team_model = get_team_by_search_code(search_code, db)

        if not team_model:
            raise PydanticCustomError(
                "team_model", f"Group with code '{search_code}' not found."
            )

        elif current_user in team_model.users:
            raise PydanticCustomError(
                "already_member",
                f"You are already a member of group {team_model.name}#{search_code}.",
            )

        join_team(team_model=team_model, user=current_user, db=db)

        return responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    except PydanticCustomError as e:
        errors.append(e.message())
    except Exception as e:
        # Handle unexpected DB errors during the join process
        errors.append(f"An unexpected error occurred while joining the group: {e}")
    print("errors", errors)

    # Re-render with errors
    return templates.TemplateResponse(
        template_name,
        {
            "form": form,
            "request": request,
            "errors": errors,
            "search_code": search_code,
            "search_code_value": search_code,
        },
    )


@router.post(
    "/team/{team_id}/{user_id}/{approve}",
    status_code=status.HTTP_302_FOUND,
    name="team.decide_join_request",
)
async def decide_join_request(
    team_id: int,
    user_id: int,
    approve: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """
    Handles the POST request to accept a user's join request to a team.
    """
    # 1. Authorization Check: Is the current user an owner/admin of this team?
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    if team.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to accept members.",
        )

    decide_join_team(team_id, user_id, approve, db)
    redirect_url = f"/team/{team_id}"

    return responses.RedirectResponse(
        url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
    )


@router.post(
    "/{team_id}/join_requests/accept_all",
    status_code=status.HTTP_302_FOUND,
)
async def accept_all_join_requests(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Group not found")

    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    from backend.db.repository.team import approve_all_join_requests
    approve_all_join_requests(team.id, db)
    
    return responses.RedirectResponse(
        url=f"/team/{team_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/{team_id}")
async def team_view(
    request: Request,
    team_id: int,
    sort: str = "games_count",
    order: str = "desc",
    year: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {"error": "Group not found"}
        
    # Get available years
    team_games = db.query(Game).filter(Game.team_id == team_id).all()
    print(f"DEBUG: Found {len(team_games)} games for team {team_id}")
    all_years = set()
    for g in team_games:
        if g.date:
             all_years.add(int(str(g.date)[:4]))
    available_years = sorted(list(all_years), reverse=True)
    print(f"DEBUG: Available years: {available_years}")
    
    target_year = None
    if year and year != "all":
         try: target_year = int(year)
         except: pass

    from backend.db.repository.team import get_team_player_stats_bulk
    
    join_requests = get_team_join_requests(team, db)
    players_info = []
    
    # helper for bulk fetch
    bulk_stats = get_team_player_stats_bulk(team.id, db, year=target_year)
    
    for player in get_team_approved_players(team, db):
        p_stats = bulk_stats.get(player.id, {"games_count": 0, "total_balance": 0.0})
        
        # Filter inactive players if Year filter is active
        if target_year and p_stats["games_count"] == 0:
            continue

        players_info.append(
            {
                "player": player,
                "games_count": p_stats["games_count"],
                "total_balance": p_stats["total_balance"],
            }
        )

    # Sorting
    reverse_order = (order == "desc")
    
    if sort == "player":
        players_info.sort(key=lambda x: x["player"].nick.lower(), reverse=reverse_order)
    elif sort == "games_count":
        players_info.sort(key=lambda x: x["games_count"], reverse=reverse_order)
    elif sort == "balance":
        players_info.sort(key=lambda x: x["total_balance"], reverse=reverse_order)
    else:
        # Default
        players_info.sort(key=lambda x: x["games_count"], reverse=True)

    return templates.TemplateResponse(
        "team/team_view.html",
        {
            "request": request,
            "current_user": user,
            "team": team,
            "join_requests": join_requests,
            "players_info": players_info,
            "sort_by": sort,
            "order": order,
            "available_years": available_years,
            "selected_year": year if year else "all",
        },
    )


@router.get("/{team_id}/player/{player_id}")
async def player_stats(
    request: Request,
    team_id: int,
    player_id: int,
    sort: str = "date",
    order: str = "desc",
    year: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    from backend.db.repository.game import get_player_games_stats_bulk
    
    team = get_team_by_id(team_id, db)
    if not team:
        return RedirectResponse("/")

    # Verify user is in team
    if user not in team.users:
        return RedirectResponse("/")

    player = get_user(player_id, db)
    if not player:
        return RedirectResponse(f"/team/{team_id}")

    # Get games for this player IN THIS TEAM, ALL of them
    team_games = get_user_team_games(player, team_id, db, limit=None)
    
    # Extract years and Filter
    available_years = sorted(list(set([int(str(g.date)[:4]) for g in team_games])), reverse=True)
    if year and year != "all":
        try:
            target_year = int(year)
            team_games = [g for g in team_games if int(str(g.date)[:4]) == target_year]
        except ValueError:
            pass
    
    # Bulk fetch stats
    bulk_stats = get_player_games_stats_bulk(player.id, team.id, db)

    games_history = []
    total_seconds_played = 0

    for game in team_games:
        stats = bulk_stats.get(game.id, {"balance": 0.0, "total_pot": 0.0, "players_count": 0})
        
        games_history.append({
            "game": game, 
            "balance": stats["balance"],
            "total_pot": stats["total_pot"],
            "players_count": stats["players_count"]
        })
        
        # Calculate duration if times are available
        if game.start_time and game.finish_time:
            duration = (game.finish_time - game.start_time).total_seconds()
            if duration > 0:
                total_seconds_played += duration
        
    total_balance = sum(g["balance"] for g in games_history)
    
    # Calculate Winrate (Won / Hour)
    hours_played = total_seconds_played / 3600
    winrate = 0
    if hours_played > 0:
        winrate = total_balance / hours_played
    
    # --- Advanced Stats ---
    from backend.db.models.buy_in import BuyIn
    from backend.db.models.add_on import AddOn
    from sqlalchemy import func
    from collections import defaultdict

    # 1. Team Context
    q_team_games = db.query(Game).filter(Game.team_id == team.id)
    if year and year != "all":
         q_team_games = q_team_games.filter(Game.date.like(f"{target_year}%"))
    team_total_games = q_team_games.count()
    
    q_bi = db.query(func.sum(BuyIn.amount)).join(Game).filter(Game.team_id == team.id)
    q_ao = db.query(func.sum(AddOn.amount)).join(Game).filter(Game.team_id == team.id, AddOn.status == PlayerRequestStatus.APPROVED)
    if year and year != "all":
        q_bi = q_bi.filter(Game.date.like(f"{target_year}%"))
        q_ao = q_ao.filter(Game.date.like(f"{target_year}%"))
    team_total_pot = (q_bi.scalar() or 0) + (q_ao.scalar() or 0)

    # 2. Player Details
    total_investment = 0.0
    wins_count = 0; losses_count = 0; draws_count = 0
    best_result = None; worst_result = None
    
    game_ids = [g.id for g in team_games]
    if game_ids:
        # Investment calculation
        user_bi = db.query(BuyIn.game_id, func.sum(BuyIn.amount)).filter(BuyIn.user_id == player.id, BuyIn.game_id.in_(game_ids)).group_by(BuyIn.game_id).all()
        user_ao = db.query(AddOn.game_id, func.sum(AddOn.amount)).filter(AddOn.user_id == player.id, AddOn.game_id.in_(game_ids), AddOn.status==PlayerRequestStatus.APPROVED).group_by(AddOn.game_id).all()
        
        invest_map = defaultdict(float)
        for gid, amt in user_bi: invest_map[gid] += amt
        for gid, amt in user_ao: invest_map[gid] += amt
        
        for g_data in games_history:
            gid = g_data["game"].id
            inv = invest_map[gid]
            bal = g_data["balance"]
            
            total_investment += inv
            
            if bal > 0.01: wins_count += 1
            elif bal < -0.01: losses_count += 1
            else: draws_count += 1
            
            if best_result is None or bal > best_result["balance"]:
                best_result = {"balance": bal, "date": g_data["game"].date}
            if worst_result is None or bal < worst_result["balance"]:
                worst_result = {"balance": bal, "date": g_data["game"].date}

    games_count = len(team_games)
    
    # Additional Stats: Variance & Monthly
    import math
    avg_balance = (total_balance / games_count) if games_count else 0
    variance = 0
    std_dev = 0
    monthly_balances = defaultdict(lambda: {"balance": 0.0, "count": 0})
    
    if games_history:
        # Variance
        variance = sum((g["balance"] - avg_balance) ** 2 for g in games_history) / len(games_history)
        std_dev = math.sqrt(variance)
        
        # Monthly Aggregation
        for g in games_history:
            m_key = str(g["game"].date)[:7]
            monthly_balances[m_key]["balance"] += g["balance"]
            monthly_balances[m_key]["count"] += 1
            
    sorted_months = sorted(monthly_balances.items(), key=lambda x: x[0], reverse=True)

    # Volatility Rating (Std Dev relative to Avg Buy-in)
    volatility_index = 0
    volatility_label = "N/A"
    avg_buyin_val = (total_investment / games_count) if games_count else 0
    
    # --- Team Context & Rankings ---
    from backend.db.models.cash_out import CashOut
    
    filters = [Game.team_id == team.id]
    if year and year != "all":
        filters.append(Game.date.like(f"{target_year}%"))
        
    bis = db.query(BuyIn.user_id, BuyIn.game_id, BuyIn.amount).join(Game).filter(*filters).all()
    aos = db.query(AddOn.user_id, AddOn.game_id, AddOn.amount).join(Game).filter(*filters, AddOn.status == PlayerRequestStatus.APPROVED).all()
    cos = db.query(CashOut.user_id, CashOut.game_id, CashOut.amount).join(Game).filter(*filters).all()
    
    p_net = defaultdict(lambda: defaultdict(float))
    p_inv = defaultdict(lambda: defaultdict(float))
    
    for u, g, a in bis: 
        p_net[u][g] -= a
        p_inv[u][g] += a
    for u, g, a in aos: 
        p_net[u][g] -= a
        p_inv[u][g] += a
    for u, g, a in cos: p_net[u][g] += a
    
    player_metrics = {}
    team_vols = []
    
    # Calculate Pot Size per Game
    game_pot_sizes = defaultdict(float)
    for u, g, a in bis: game_pot_sizes[g] += a
    for u, g, a in aos: game_pot_sizes[g] += a
    
    for uid, g_map in p_net.items():
        bals = list(g_map.values())
        if len(bals) < 1: continue 
        
        n_games = len(bals) # Active games
        m = sum(bals) / n_games
        v = sum((b - m)**2 for b in bals) / n_games if n_games > 1 else 0
        sd = math.sqrt(v)
        
        invs = list(p_inv[uid].values())
        total_inv = sum(invs)
        avg_inv = total_inv / n_games if n_games else 0
        roi = (sum(bals) / total_inv * 100) if total_inv else -999.0
        
        my_played_gids = g_map.keys()
        total_pot_played = sum(game_pot_sizes[gid] for gid in my_played_gids)
        pot_share = (sum(bals) / total_pot_played * 100) if total_pot_played else 0.0
        
        vol_idx = (sd / avg_inv) if avg_inv > 0 else 0
        if vol_idx > 0: team_vols.append(vol_idx)
        
        player_metrics[uid] = {
            "std_dev": sd,
            "avg_buyin": avg_inv,
            "avg_profit": m,
            "roi": roi,
            "pot_share": pot_share,
            "vol_idx": vol_idx
        }
        
    avg_team_vol_idx = sum(team_vols) / len(team_vols) if team_vols else 0
    
    def get_rank_tier(metric, my_uid, lower_is_better=False, tier_labels=("Low", "Average", "High")):
        if my_uid not in player_metrics: return None
        
        values = sorted([m[metric] for m in player_metrics.values()], reverse=not lower_is_better)
        my_val = player_metrics[my_uid][metric]
        
        try:
            rank = values.index(my_val) + 1
        except ValueError: return None
            
        total = len(values)
        pct = (rank / total) * 100
        top_pct = math.ceil(pct)
        
        # Tier Assignment (3 buckets)
        if rank <= total / 3: tier = tier_labels[0]
        elif rank <= 2 * total / 3: tier = tier_labels[1]
        else: tier = tier_labels[2]
        
        return {"rank": rank, "total": total, "top_pct": top_pct, "tier": tier}

    # Rankings
    ranks = {
        # Lower SD is "Low" tier
        "std_dev": get_rank_tier("std_dev", player_id, lower_is_better=True),
        # Lower Buyin is "Low" tier
        "avg_buyin": get_rank_tier("avg_buyin", player_id, lower_is_better=True),
        # Higher Profit is "Top X%"
        "avg_profit": get_rank_tier("avg_profit", player_id, lower_is_better=False),
        "roi": get_rank_tier("roi", player_id, lower_is_better=False),
        "pot_share": get_rank_tier("pot_share", player_id, lower_is_better=False),
        # Volatility Index: "Low" is better (stable)? User said "Game Swings... Low/Medium/High".
        # If I use lower_is_better=True (Low Vol), rank 1 is Low Vol.
        "game_swings": get_rank_tier("vol_idx", player_id, lower_is_better=True, tier_labels=("Low", "Average", "High"))
    }
    
    if avg_buyin_val > 0:
        volatility_index = std_dev / avg_buyin_val
        # Determine label from Rank
        if ranks["game_swings"]:
            volatility_label = ranks["game_swings"]["tier"] + " (Vs Team)"
        else:
            volatility_label = "N/A"
            
    # Fallback absolute check if Team data missing
    if volatility_label == "N/A":
         if volatility_index < 0.8: volatility_label = "Very Low"
         elif volatility_index < 1.5: volatility_label = "Low"
         elif volatility_index < 3.0: volatility_label = "Average"
         else: volatility_label = "High"
        
    # Team Comparisons
    team_aggregates = {"games": [], "roi": [], "attendance": [], "avg_buyin": [], "avg_profit": []}
    for uid, s in bulk_stats.items():
        g = s.get("games_count", 0)
        if g > 0:
            inv = s.get("total_investment", 0)
            bal = s.get("total_balance", 0)
            team_aggregates["games"].append(g)
            team_aggregates["attendance"].append(g / team_total_games * 100 if team_total_games else 0)
            team_aggregates["avg_profit"].append(bal / g)
            if inv > 0:
                team_aggregates["avg_buyin"].append(inv / g)
                team_aggregates["roi"].append(bal / inv * 100)
                
    def safe_avg(lst): return sum(lst) / len(lst) if lst else 0
    
    adv_stats_team = {
        "games_count": safe_avg(team_aggregates["games"]),
        "attendance_pct": safe_avg(team_aggregates["attendance"]),
        "avg_buyin": safe_avg(team_aggregates["avg_buyin"]),
        "avg_balance": safe_avg(team_aggregates["avg_profit"]),
        "roi": safe_avg(team_aggregates["roi"])
    }

    adv_stats = {
        "total_investment": total_investment,
        "avg_buyin": avg_buyin_val,
        "avg_balance": avg_balance,
        "attendance_pct": (games_count / team_total_games * 100) if team_total_games else 0,
        "attendance_count": games_count,
        "team_total_games": team_total_games,
        "roi": (total_balance / total_investment * 100) if total_investment else 0,
        "pot_share_pct": player_metrics[player_id]["pot_share"] if player_id in player_metrics else 0,
        "wins": wins_count,
        "draws": draws_count,
        "losses": losses_count,
        "win_pct": (wins_count / games_count * 100) if games_count else 0,
        "best_result": best_result,
        "worst_result": worst_result,
        "last_5_games": sorted(games_history, key=lambda x: (x["game"].date), reverse=True)[:5],
        "variance": variance,
        "std_dev": std_dev,
        "typical_range_low": avg_balance - std_dev,
        "typical_range_high": avg_balance + std_dev,
        "volatility_index": volatility_index,
        "volatility_label": volatility_label,
        "avg_team_vol_idx": avg_team_vol_idx,
        "ranks": ranks,
        "team_avgs": adv_stats_team,
        "monthly_balances": sorted_months
    }

    # Prepare Chart Data (Chronological)
    chronological_games = sorted(games_history, key=lambda x: (x["game"].date, x["game"].start_time or datetime.min.time()))
    cumulative_balance = 0.0
    chart_points = []
    for g in chronological_games:
        cumulative_balance += g["balance"]
        chart_points.append({
            "date": str(g["game"].date),
            "balance": round(cumulative_balance, 2),
            "game_id": g["game"].id
        })

    # Add initial zero point to start graph from 0
    if chart_points:
        chart_points.insert(0, {
            "date": "Start",
            "balance": 0.0,
            "game_id": -1
        })

    today = datetime.now().date() 
    # Sorting
    reverse_order = (order == "desc")
    
    if sort == "date":
        games_history.sort(key=lambda x: (x["game"].date, x["game"].start_time or datetime.min.time()), reverse=reverse_order)
    elif sort == "balance":
        games_history.sort(key=lambda x: x["balance"], reverse=reverse_order)
    elif sort == "pot":
        games_history.sort(key=lambda x: x["total_pot"], reverse=reverse_order)
    else:
        # Default
        games_history.sort(key=lambda x: (x["game"].date, x["game"].start_time or datetime.min.time()), reverse=True)

    return templates.TemplateResponse(
        "team/player_stats.html",
        {
            "request": request,
            "team": team,
            "player": player,
            "games_history": games_history,
            "total_balance": total_balance,
            "games_count": len(games_history),
            "visible_count": len(games_history),
            "winrate": winrate,
            "is_owner": user.id == team.owner_id,
            "sort_by": sort,
            "order": order,
            "sort_by": sort,
            "order": order,
            "chart_points": chart_points,
            "adv_stats": adv_stats,
            "available_years": available_years,
            "selected_year": year if year else "all",
        },
    )


@router.post("/{team_id}/player/{player_id}/remove")
async def remove_player(
    request: Request,
    team_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or user.id != team.owner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    player = get_user(player_id, db)
    if player:
        remove_user_from_team(team, player, db)

    return RedirectResponse(f"/team/{team_id}", status_code=303)


@router.post("/{team_id}/delete")
async def delete_team_route(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    from backend.db.repository.team import delete_team
    
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Group not found")
        
    if user.id != team.owner_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    delete_team(team, db)

    return RedirectResponse("/", status_code=303)


@router.post("/{team_id}/import")
async def import_legacy_games(
    request: Request,
    team_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    import json
    from datetime import datetime, timedelta
    import secrets
    from backend.db.models.game import Game
    from backend.db.models.buy_in import BuyIn
    from backend.db.models.cash_out import CashOut
    from backend.db.models.user_game import UserGame
    from backend.db.models.user_team import UserTeam
    from backend.core.hashing import Hasher
    from backend.db.repository.team import create_new_user

    uploaded_file = file
    
    if not uploaded_file:
         raise HTTPException(status_code=400, detail="No file uploaded")
         
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Group not found")
        
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        content = await uploaded_file.read()
        data = json.loads(content)
        
        if not isinstance(data, list):
             raise ValueError("JSON must be a list of game objects")
             
        # Cache existing team users for lookup
        # Nickname matching is case-sensitive or insensitive? Let's do sensitive for now or match closely.
        # User defined nick might vary.
        team_users_map = {u.nick: u for u in team.users}

        def get_or_create_team_user(nick_name):
            if not nick_name: return None
            if nick_name in team_users_map:
                return team_users_map[nick_name]
            
            # Create Guest User
            random_suffix = secrets.token_hex(4)
            new_email = f"{nick_name.lower().replace(' ', '_')}_{random_suffix}@imported.legacy"
            
            player_user = User(
                email=new_email,
                nick=nick_name,
                hashed_password=Hasher.get_password_hash("guest_imported"),
                is_active=True
            )
            db.add(player_user)
            db.commit()
            db.refresh(player_user)
            
            ut = UserTeam(
                user_id=player_user.id,
                team_id=team.id,
                status=PlayerRequestStatus.APPROVED
            )
            db.add(ut)
            db.commit()
            
            team_users_map[nick_name] = player_user
            return player_user
        
        imported_count = 0
        skipped_count = 0
        
        for g_data in data:
            # 1. Parse Date/Time
            start_str = g_data.get("start_time") # "YYYY-MM-DD HH:MM"
            finish_str = g_data.get("finish_time") # "YYYY-MM-DD HH:MM"
            
            dt_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            dt_finish = datetime.strptime(finish_str, "%Y-%m-%d %H:%M")
            g_date = dt_start.date()
                
            # 2. Check Duplicates
            exists = db.query(Game).filter(
                Game.team_id == team.id,
                Game.start_time == dt_start
            ).first()
            
            if exists:
                skipped_count += 1
                continue

            # 3. Determine Owner (Host)
            host_nick = g_data.get("host")
            game_owner_id = team.owner_id
            if host_nick:
                host_user = get_or_create_team_user(host_nick)
                if host_user:
                    game_owner_id = host_user.id
                
            # 4. Create Game
            new_game = Game(
                date=g_date,
                start_time=dt_start,
                finish_time=dt_finish,
                default_buy_in=0,
                running=False,
                owner_id=game_owner_id,
                team_id=team.id
            )
            db.add(new_game)
            db.commit()
            db.refresh(new_game)
            
            # 5. Process Players
            players_list = g_data.get("players", [])
            for p_data in players_list:
                nick = p_data.get("nick")
                buy_in_amt = float(p_data.get("buy_in", 0))
                cash_out_amt = float(p_data.get("cash_out", 0))
                
                player_user = get_or_create_team_user(nick)
                
                # Add to Game
                ug = UserGame(user_id=player_user.id, game_id=new_game.id)
                db.add(ug)
                
                # Stats
                if buy_in_amt > 0:
                    bi = BuyIn(
                        amount=buy_in_amt,
                        user_id=player_user.id,
                        game_id=new_game.id,
                        time=dt_start
                    )
                    db.add(bi)
                    
                if cash_out_amt > 0: 
                    co = CashOut(
                        amount=cash_out_amt,
                        user_id=player_user.id,
                        game_id=new_game.id,
                        time=dt_finish,
                        status=PlayerRequestStatus.APPROVED
                    )
                    db.add(co)
                elif buy_in_amt > 0:
                    co = CashOut(
                        amount=0,
                        user_id=player_user.id,
                        game_id=new_game.id,
                        time=dt_finish,
                        status=PlayerRequestStatus.APPROVED
                    )
                    db.add(co)

            db.commit()
            imported_count += 1
            
        msg = f"Imported {imported_count} games. Skipped {skipped_count} duplicates."
        return RedirectResponse(f"/team/{team_id}?msg={msg}", status_code=303)
        
    except Exception as e:
        # Check if json error
        return RedirectResponse(f"/team/{team_id}?errors=Import failed: {str(e)}", status_code=303)
