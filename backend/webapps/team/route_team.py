import json
import unicodedata
from datetime import datetime
from sqlite3 import IntegrityError
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Request,
    responses,
    HTTPException,
    Form,
    UploadFile,
    File,
)
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from backend.apis.v1.route_login import (
    get_current_user,
    get_current_user_from_token,
    get_active_user,
)
from backend.core.config import TEMPLATES_DIR
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.db.models.team import Team
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.models.user_team import UserTeam
from backend.db.models.team_role import TeamRole
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
    is_user_admin,
    is_user_privileged_for_team,
)
from backend.db.session import get_db
from backend.schemas.team import TeamCreate
from backend.schemas.user import UserCreate
from backend.webapps.team.forms import TeamCreateForm, TeamJoinForm
from backend.webapps.chip_structure.chip_structure_form import ChipStructureCreateForm
from backend.db.repository.chip_structure import (
    list_team_chip_structures,
    delete_chip_structure,
    set_default_chip_structure,
    get_chip_structure,
    create_new_chip_structure_db,
    update_chip_structure_db,
)
import os
from sqlalchemy import select

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter()


@router.get("/{team_id}/chip_structures", name="team.manage_chip_structures")
async def manage_chip_structures(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    chip_structures = list_team_chip_structures(team_id, db)
    return templates.TemplateResponse(
        "team/manage_chip_structures.html",
        {
            "request": request,
            "team": team,
            "chip_structures": chip_structures,
        },
    )


@router.get("/{team_id}/chip_structures/create", name="team.create_chip_structure_form")
async def create_cs_form(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    return templates.TemplateResponse(
        "team/edit_chip_structure.html",
        {"request": request, "team": team, "chip_structure": None, "form": {}},
    )


@router.post("/{team_id}/chip_structures/create", name="team.create_chip_structure")
async def create_cs(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    form = await request.form()
    form_data = {
        **form,
        "color": form.getlist("color"),
        "value": form.getlist("value"),
        "team_id": team_id,
        "created_by": current_user.id,
    }

    try:
        cs_form = ChipStructureCreateForm(**form_data)
        create_new_chip_structure_db(cs_form, db)
        return RedirectResponse(
            f"/team/{team_id}/chip_structures", status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return templates.TemplateResponse(
            "team/edit_chip_structure.html",
            {
                "request": request,
                "team": team,
                "chip_structure": None,
                "form": form_data,
                "errors": [str(e)],
            },
        )


@router.get("/{team_id}/chip_structures/{cs_id}/edit", name="team.edit_chip_structure_form")
async def edit_cs_form(
    request: Request,
    team_id: int,
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    cs = get_chip_structure(cs_id, db)
    return templates.TemplateResponse(
        "team/edit_chip_structure.html",
        {"request": request, "team": team, "chip_structure": cs, "form": {}},
    )


@router.post("/{team_id}/chip_structures/{cs_id}/edit", name="team.edit_chip_structure")
async def edit_cs(
    request: Request,
    team_id: int,
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    form = await request.form()
    form_data = {
        **form,
        "color": form.getlist("color"),
        "value": form.getlist("value"),
        "team_id": team_id,
        "created_by": current_user.id,
    }

    try:
        cs_form = ChipStructureCreateForm(**form_data)
        update_chip_structure_db(cs_id, cs_form, db)
        return RedirectResponse(
            f"/team/{team_id}/chip_structures", status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        cs = get_chip_structure(cs_id, db)
        return templates.TemplateResponse(
            "team/edit_chip_structure.html",
            {
                "request": request,
                "team": team,
                "chip_structure": cs,
                "form": form_data,
                "errors": [str(e)],
            },
        )


@router.post("/{team_id}/chip_structures/{cs_id}/delete", name="team.delete_chip_structure")
async def delete_cs(
    team_id: int,
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        delete_chip_structure(cs_id, db)
        return RedirectResponse(
            f"/team/{team_id}/chip_structures?msg=Chip structure deleted successfully",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return RedirectResponse(
            f"/team/{team_id}/chip_structures?error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{team_id}/chip_structures/{cs_id}/set_default", name="team.set_default_chip_structure")
async def set_default_cs(
    team_id: int,
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team or not is_user_privileged_for_team(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    set_default_chip_structure(team_id, cs_id, db)
    return RedirectResponse(
        f"/team/{team_id}/chip_structures", status_code=status.HTTP_303_SEE_OTHER
    )


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

    if not is_user_admin(current_user.id, team.id, db):
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

    if not is_user_admin(current_user.id, team.id, db):
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
    all_years = set()
    for g in team_games:
        if g.date:
            all_years.add(int(str(g.date)[:4]))
    available_years = sorted(list(all_years), reverse=True)

    target_year = None
    if year and year != "all":
        try:
            target_year = int(year)
        except:
            pass

    # --- Stats for Header & Modal ---
    # Use the shared helper to get full stats including rankings
    # Pass 'year' directly (it's a string or None from query param)
    stats = _calculate_team_stats(team, year, db)
    # ------------------------

    from backend.db.repository.team import get_team_player_stats_bulk

    join_requests = get_team_join_requests(team, db)
    players_info = []

    # helper for bulk fetch
    bulk_stats = get_team_player_stats_bulk(team.id, db, year=target_year)

    current_user_assoc = db.query(UserTeam).filter(UserTeam.team_id == team.id, UserTeam.user_id == user.id).one_or_none()
    is_admin = current_user_assoc and current_user_assoc.role == TeamRole.ADMIN

    for player in get_team_approved_players(team, db):
        p_stats = bulk_stats.get(player.id, {"games_count": 0, "total_balance": 0.0})

        # Filter inactive players if Year filter is active
        if target_year and p_stats["games_count"] == 0:
            continue

        # Fetch player role in this team
        p_assoc = db.query(UserTeam).filter(UserTeam.team_id == team.id, UserTeam.user_id == player.id).one_or_none()
        p_role = p_assoc.role.value if p_assoc else 'MEMBER'

        players_info.append(
            {
                "player": player,
                "games_count": p_stats["games_count"],
                "total_balance": p_stats["total_balance"],
                "player_role": p_role,
            }
        )

    # Sorting
    reverse_order = order == "desc"

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
            "is_admin": is_admin,
            "team": team,
            "join_requests": join_requests,
            "players_info": players_info,
            "sort_by": sort,
            "order": order,
            "available_years": available_years,
            "selected_year": year if year else "all",
            "stats": stats,
        },
    )


@router.get("/{team_id}/player/{player_id}")
async def player_stats(
    request: Request,
    team_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
    year: str = "all",
    sort: str = "date",
    order: str = "desc",
):
    context = await _get_player_stats_context(
        request, team_id, player_id, db, current_user, year, sort, order
    )
    if isinstance(context, RedirectResponse):
        return context
    return templates.TemplateResponse("team/player_stats.html", context)


@router.get("/{team_id}/player/{player_id}/advanced")
async def player_stats_advanced(
    request: Request,
    team_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
    year: str = "all",
    sort: str = "date",
    order: str = "desc",
):
    context = await _get_player_stats_context(
        request, team_id, player_id, db, current_user, year, sort, order
    )
    if isinstance(context, RedirectResponse):
        return context
    return templates.TemplateResponse("team/player_stats_advanced.html", context)


@router.get("/{team_id}/stats", name="team_stats")
async def team_stats(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
    year: str = "all",
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return RedirectResponse(f"/dashboard")

    # Check permissions
    if (
        current_user.id not in [m.id for m in team.users]
        and not current_user.is_superuser
    ):
        return RedirectResponse(f"/dashboard")

    # Available years for the filter
    team_games = db.query(Game).filter(Game.team_id == team_id).all()
    all_years = set()
    for g in team_games:
        if g.date:
            all_years.add(int(str(g.date)[:4]))
    available_years = sorted(list(all_years), reverse=True)

    stats = _calculate_team_stats(team, year, db)

    return templates.TemplateResponse(
        "team/team_stats.html",
        {
            "request": request,
            "team": team,
            "stats": stats,
            "selected_year": year,
            "available_years": available_years,
        },
    )


async def _get_player_stats_context(
    request: Request,
    team_id: int,
    player_id: int,
    db: Session,
    current_user: User,
    year: str = "all",
    sort: str = "date",
    order: str = "desc",
):
    from backend.db.models.buy_in import BuyIn
    from backend.db.models.add_on import AddOn
    from backend.db.models.cash_out import CashOut
    from sqlalchemy import func
    from collections import defaultdict
    import math
    from datetime import datetime, timedelta
    
    def get_time_weight(game_date, current_date=None):
        """
        Calculate time-based weight for a game based on how long ago it was played.
        
        Goals:
        - Games from last 6 months: weight ≈ 0.95-1.0 (nearly full weight)
        - Games from 1-2 years ago: weight ≈ 0.4-0.6
        - Games from 3+ years ago: weight ≈ 0.2 (5x less important than recent)
        
        Uses exponential decay with a grace period for recent games.
        """
        if current_date is None:
            current_date = datetime.now().date()
        
        # Handle string dates (convert from 'YYYY-MM-DD' format)
        if isinstance(game_date, str):
            game_date = datetime.strptime(game_date, '%Y-%m-%d').date()
        # Handle datetime objects
        elif isinstance(game_date, datetime):
            game_date = game_date.date()
        
        # Handle current_date conversion
        if isinstance(current_date, str):
            current_date = datetime.strptime(current_date, '%Y-%m-%d').date()
        elif isinstance(current_date, datetime):
            current_date = current_date.date()
            
        days_ago = (current_date - game_date).days
        
        # Parameters tuned to meet requirements
        recent_threshold_days = 180  # 6 months - minimal decay within this period
        decay_rate = 0.0018  # Controls decay rate after threshold (tuned for ~5x difference at 3 years)
        
        if days_ago <= recent_threshold_days:
            # Recent games: minimal decay (95-100% weight)
            return 1.0 - (days_ago / recent_threshold_days) * 0.05
        else:
            # Older games: exponential decay
            excess_days = days_ago - recent_threshold_days
            return 0.95 * math.exp(-decay_rate * excess_days)

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return RedirectResponse(f"/dashboard")

    # Check permissions
    if current_user.id not in [m.id for m in team.users] and not current_user.is_superuser:
        return RedirectResponse(f"/dashboard")
    
    # Check player role for admin actions
    is_admin = False
    player_role = "MEMBER"
    for m in team.users:
        if m.id == current_user.id:
            membership = (
                db.query(UserTeam)
                .filter(UserTeam.team_id == team.id, UserTeam.user_id == current_user.id)
                .first()
            )
            if membership and membership.role == TeamRole.ADMIN:
                is_admin = True
        
        if m.id == player_id:
             p_membership = (
                db.query(UserTeam)
                .filter(UserTeam.team_id == team.id, UserTeam.user_id == player_id)
                .first()
            )
             if p_membership:
                 player_role = p_membership.role

    player = db.query(User).filter(User.id == player_id).first()
    if not player:
        return RedirectResponse(f"/team/{team_id}")

    # Build filters
    filters = [Game.team_id == team.id]
    target_year = None
    if year and year != "all":
        target_year = year
        filters.append(Game.date.like(f"{target_year}%"))

    # Fetch all games for this team (filtered by year)
    q_games = db.query(Game).filter(*filters).order_by(Game.date.desc())
    all_team_games = q_games.all()
    team_total_games = len(all_team_games)
    
    team_game_ids = [g.id for g in all_team_games]
    
    # Determine available years for filter
    # To get available years we need ALL games for the team, unqualified by year filter
    all_dates = db.query(Game.date).filter(Game.team_id == team.id).all()
    available_years = sorted(
        list(set([str(d[0])[:4] for d in all_dates if d[0]])), reverse=True
    )

    # Calculate stats for the specific player
    # 1. Get games where player participated
    # Participation is defined by having a BuyIn or AddOn or CashOut? Or just being in the game?
    # Usually we use BuyIn as participation marker.
    
    # We need to calculate balance for each game for this player
    # Balance = CashOut - (BuyIn + AddOn)
    
    # Optimization: Fetch all transactions for this player in these games
    p_buyins = db.query(BuyIn).filter(BuyIn.user_id == player_id, BuyIn.game_id.in_(team_game_ids)).all()
    p_addons = db.query(AddOn).filter(AddOn.user_id == player_id, AddOn.game_id.in_(team_game_ids), AddOn.status == PlayerRequestStatus.APPROVED).all()
    p_cashouts = db.query(CashOut).filter(CashOut.user_id == player_id, CashOut.game_id.in_(team_game_ids)).all()

    game_stats = defaultdict(lambda: {"buyin": 0.0, "addon": 0.0, "cashout": 0.0})
    played_game_ids = set()

    for b in p_buyins:
        game_stats[b.game_id]["buyin"] += b.amount
        played_game_ids.add(b.game_id)
    for a in p_addons:
        game_stats[a.game_id]["addon"] += a.amount
        played_game_ids.add(a.game_id)
    for c in p_cashouts:
        game_stats[c.game_id]["cashout"] += c.amount
        # Cashout implies participation usually, but let's stick to buyin/addon as entry.
        # If someone has cashout but no buyin, it's weird, but they played.
        played_game_ids.add(c.game_id)

    games_history = []
    total_investment = 0.0
    total_balance = 0.0
    wins_count = 0
    draws_count = 0
    losses_count = 0
    best_result = None
    worst_result = None
    
    # Calculate Total Pot per game for display
    # This is expensive if we do it for every game individually.
    # Let's fetch total pot for the team_games
    # Total Pot = Sum(BuyIns) + Sum(AddOns) for that game
    game_pots = defaultdict(float)
    all_bi = db.query(BuyIn.game_id, BuyIn.amount).filter(BuyIn.game_id.in_(team_game_ids)).all()
    all_ao = db.query(AddOn.game_id, AddOn.amount).filter(AddOn.game_id.in_(team_game_ids), AddOn.status == PlayerRequestStatus.APPROVED).all()
    
    for gid, amt in all_bi:
        game_pots[gid] += amt
    for gid, amt in all_ao:
        game_pots[gid] += amt
        
    # Also need player count per game
    game_player_counts = defaultdict(int)
    # Count distinct users per game in BuyIn
    # This is an approximation but fast enough. 
    # Or cleaner: db.query(BuyIn.game_id, func.count(func.distinct(BuyIn.user_id))).group_by(BuyIn.game_id)
    gpc_query = db.query(BuyIn.game_id, func.count(func.distinct(BuyIn.user_id))).filter(BuyIn.game_id.in_(team_game_ids)).group_by(BuyIn.game_id).all()
    for gid, count in gpc_query:
        game_player_counts[gid] = count

    # Prep games_history
    games_map = {g.id: g for g in all_team_games}
    
    monthly_balances = defaultdict(lambda: {"balance": 0.0, "count": 0})

    for gid in played_game_ids:
        s = game_stats[gid]
        inv = s["buyin"] + s["addon"]
        cash = s["cashout"]
        bal = cash - inv
        
        total_investment += inv
        total_balance += bal
        
        if bal > 0.01:
            wins_count += 1
        elif bal < -0.01:
            losses_count += 1
        else:
            draws_count += 1
            
        if best_result is None or bal > best_result:
            best_result = bal
        if worst_result is None or bal < worst_result:
            worst_result = bal
            
        games_history.append({
            "game": games_map[gid],
            "balance": bal,
            "total_pot": game_pots[gid],
            "players_count": game_player_counts[gid]
        })

        # Monthly Aggregation
        m_key = str(games_map[gid].date)[:7]
        monthly_balances[m_key]["balance"] += bal
        monthly_balances[m_key]["count"] += 1

    games_count = len(games_history)
    avg_balance = total_balance / games_count if games_count else 0
    avg_buyin_val = total_investment / games_count if games_count else 0
    
    # --- Time-weighted statistics for Bayesian analysis ---
    # Calculate weighted average balance and weighted variance
    # Recent games have more influence on predictions
    total_weight = 0.0
    weighted_balance_sum = 0.0
    
    for g in games_history:
        game = g["game"]
        weight = get_time_weight(game.date)
        g["weight"] = weight  # Store for later use
        
        total_weight += weight
        weighted_balance_sum += weight * g["balance"]
    
    # Weighted average balance (used in Bayesian likelihood)
    weighted_avg_balance = weighted_balance_sum / total_weight if total_weight > 0 else avg_balance
    
    # Weighted variance and standard deviation
    weighted_variance_sum = 0.0
    for g in games_history:
        weighted_variance_sum += g["weight"] * ((g["balance"] - weighted_avg_balance) ** 2)
    
    weighted_variance = weighted_variance_sum / total_weight if total_weight > 0 else 0
    weighted_std_dev = math.sqrt(weighted_variance)
    
    # Effective sample size (accounts for time-based weighting)
    # This is used as 'n' in the Bayesian calculation
    effective_n_games = total_weight
    
    # Calculate durations for winrate
    total_hours = 0
    for g in games_history:
        game = g["game"]
        if game.start_time and game.finish_time:
            dur = (game.finish_time - game.start_time).total_seconds() / 3600
            total_hours += dur
            
    winrate = total_balance / total_hours if total_hours > 0 else 0

    if games_history:
        # Non-weighted variance (for display purposes)
        variance = sum((g["balance"] - avg_balance) ** 2 for g in games_history) / len(
            games_history
        )
        std_dev = math.sqrt(variance)
    else:
        variance = 0
        std_dev = 0
    sorted_months = sorted(monthly_balances.items(), key=lambda x: x[0], reverse=False)

    # Volatility Rating (Std Dev relative to Avg Buy-in)
    volatility_index = 0
    volatility_label = "N/A"
    
    # --- Team Context & Rankings ---
    # We need bulk stats for ALL players in the team (filtered by year) to calculate rankings
    # This might be heavy, but necessary for "Advanced Stats".
    # We can reuse `get_player_games_stats_bulk` which was likely used before?
    # Yes, previous code used `get_player_games_stats_bulk`.
    # To save time writing all that aggregation logic again, I should use the helper if available.
    # But `get_player_games_stats_bulk` calculates per-game stats for a player.
    # We need per-player stats for the team.
    
    # Let's try to infer the previous implementation of bulk stats.
    # It queried BuyIn, AddOn, CashOut for the team+year.
    
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
    for u, g, a in cos:
        p_net[u][g] += a
        
    # Helpers for Win Share etc
    game_pos_sum = defaultdict(float)
    for u, g_map in p_net.items():
        for gid, bal in g_map.items():
            if bal > 0:
                game_pos_sum[gid] += bal
                
    # Duration map
    g_durations = {}
    for g in all_team_games:
        if g.start_time and g.finish_time:
             g_durations[g.id] = (g.finish_time - g.start_time).total_seconds() / 3600
        else:
             g_durations[g.id] = 0

    player_metrics = {}
    team_vols = []
    
    for uid, g_map in p_net.items():
        bals = list(g_map.values())
        if not bals: continue
        
        n = len(bals)
        t_bal = sum(bals)
        m = t_bal / n
        v = sum((b - m) ** 2 for b in bals) / n if n > 1 else 0
        sd = math.sqrt(v)
        
        invs = list(p_inv[uid].values())
        t_inv = sum(invs)
        avg_inv_p = t_inv / n if n else 0
        roi_p = (t_bal / t_inv * 100) if t_inv else -999.0
        
        wins_p = sum(1 for b in bals if b > 0.01)
        win_pct_p = (wins_p / n * 100) if n else 0
        
        my_gids = g_map.keys()
        
        # Win Share: my balance vs other winners sum of balance
        total_winnings_in_all_games = sum(game_pos_sum.values())
        
        if total_winnings_in_all_games > 0:
            win_share_p = t_bal / total_winnings_in_all_games * 100
        else:
            win_share_p = 100.0 if t_bal > 0 else 0.0
        
        # Hourly
        my_hours = sum(g_durations.get(gid, 0) for gid in my_gids)
        hourly_p = (t_bal / my_hours) if my_hours > 0 else 0
        
        best_p = max(bals) if bals else 0
        worst_p = min(bals) if bals else 0
        
        vol_idx_p = (sd / avg_inv_p) if avg_inv_p > 0 else 0
        if vol_idx_p > 0:
            team_vols.append(vol_idx_p)
            
        player_metrics[uid] = {
            "std_dev": sd,
            "avg_buyin": avg_inv_p,
            "avg_profit": m,
            "total_balance": t_bal,
            "roi": roi_p,
            "win_share": win_share_p,
            "vol_idx": vol_idx_p,
            "win_pct": win_pct_p,
            "hourly_winrate": hourly_p,
            "best_result": best_p,
            "worst_result": worst_p,
            "games_count": n
        }

    # Ensure current player stats are matching consistent (sometimes local logic might differ slightly due to float etc)
    # We will trust the bulk calculation for consistency
    if player_id in player_metrics:
        # Override local calcs with bulk ones to match rankings?
        # Actually local calcs are fine, but let's use player_metrics for consistency in rankings
        pass
        
    avg_team_vol_idx = sum(team_vols) / len(team_vols) if team_vols else 0
    team_sds = [m["std_dev"] for m in player_metrics.values() if m["games_count"] >= 5]
    avg_team_std_dev = sum(team_sds) / len(team_sds) if team_sds else 0

    # Team Aggregates
    team_aggregates = {"games": [], "roi": [], "attendance": [], "avg_buyin": [], "avg_profit": []}
    for uid, pm in player_metrics.items():
        if pm["games_count"] > 0:
            team_aggregates["games"].append(pm["games_count"])
            team_aggregates["attendance"].append(pm["games_count"] / team_total_games * 100 if team_total_games else 0)
            team_aggregates["avg_profit"].append(pm["avg_profit"])
            if pm["avg_buyin"] > 0: # Approximating investment check
                team_aggregates["avg_buyin"].append(pm["avg_buyin"]) # Note: avg_buyin here is per game, which is what we want? 
                # Wait, earlier loop: "avg_buyin": inv / g. Yes.
                team_aggregates["roi"].append(pm["roi"])

    def safe_avg(lst):
        return sum(lst) / len(lst) if lst else 0

    adv_stats_team = {
        "games_count": safe_avg(team_aggregates["games"]),
        "attendance_pct": safe_avg(team_aggregates["attendance"]),
        "avg_buyin": safe_avg(team_aggregates["avg_buyin"]),
        "avg_balance": safe_avg(team_aggregates["avg_profit"]),
        "roi": safe_avg(team_aggregates["roi"]),
    }

    # Rank Helper
    def get_rank_tier(metric, my_uid, lower_is_better=False, tier_labels=("Low", "Average", "High")):
        if my_uid not in player_metrics: return None
        if player_metrics[my_uid]["games_count"] < 5: return None
        
        valid = [m for m in player_metrics.values() if m["games_count"] >= 5]
        values = sorted([m[metric] for m in valid], reverse=not lower_is_better)
        my_val = player_metrics[my_uid][metric]
        
        try:
            rank = values.index(my_val) + 1
        except ValueError:
            return None
            
        total = len(values)
        if total == 0: return None
        
        pct = (rank / total) * 100
        top_pct = math.ceil(pct)
        
        if rank <= total / 3: tier = tier_labels[0]
        elif rank <= 2 * total / 3: tier = tier_labels[1]
        else: tier = tier_labels[2]
        
        return {"rank": rank, "total": total, "top_pct": top_pct, "tier": tier}

    ranks = {
        "std_dev": get_rank_tier("std_dev", player_id, lower_is_better=True),
        "avg_buyin": get_rank_tier("avg_buyin", player_id, lower_is_better=False, tier_labels=("High", "Average", "Low")),
        "avg_profit": get_rank_tier("avg_profit", player_id, lower_is_better=False),
        "total_balance": get_rank_tier("total_balance", player_id, lower_is_better=False),
        "hourly_winrate": get_rank_tier("hourly_winrate", player_id, lower_is_better=False),
        "roi": get_rank_tier("roi", player_id, lower_is_better=False),
        "win_share": get_rank_tier("win_share", player_id, lower_is_better=False),
        "win_pct": get_rank_tier("win_pct", player_id, lower_is_better=False),
        "best_result": get_rank_tier("best_result", player_id, lower_is_better=False),
        "worst_result": get_rank_tier("worst_result", player_id, lower_is_better=True),
        "game_swings": get_rank_tier("vol_idx", player_id, lower_is_better=True, tier_labels=("Low", "Average", "High")),
    }

    if std_dev > 0:
        # Use 100 as the 'Base Buy-in' for scale, as per user's stake
        # This represents how many 'initial stacks' the average swing is
        volatility_index = std_dev / 100.0
        
        # Compare against the team average absolute swings (Standard Deviation)
        if avg_team_std_dev > 0:
            rel_to_team = std_dev / avg_team_std_dev
            if rel_to_team < 0.6: volatility_label = "Very Low (Vs Team)"
            elif rel_to_team < 0.9: volatility_label = "Low (Vs Team)"
            elif rel_to_team < 1.1: volatility_label = "Average (Vs Team)"
            elif rel_to_team < 1.5: volatility_label = "High (Vs Team)"
            else: volatility_label = "Extreme (Vs Team)"
        else:
            volatility_label = "Average"
    else:
        volatility_index = 0
        volatility_label = "N/A"

    # --- Bayesian Analysis ---
    # Prior: Use team average with higher variance for new players
    # If no team average exists, use mean=0 with std=3*buy-in
    
    # Determine base buy-in for variance calculation
    base_buyin = avg_buyin_val if avg_buyin_val > 0 else 100
    
    # Check if we have meaningful team statistics
    if adv_stats_team["avg_balance"] != 0 or len(team_aggregates["avg_profit"]) > 2:
        # Team average exists - use it as prior mean with higher variance
        prior_mean = adv_stats_team["avg_balance"]
        # Use higher variance (3x) for the prior to avoid overconfidence for new players
        if avg_team_std_dev > 0:
            prior_sigma = avg_team_std_dev * 3.0
        else:
            prior_sigma = base_buyin * 3.0
    else:
        # No meaningful team average - use neutral prior
        prior_mean = 0.0
        prior_sigma = base_buyin * 3.0
    
    
    # Likelihood (use time-weighted statistics for more accurate predictions)
    # Recent games have more influence on the likelihood
    likelihood_mean = weighted_avg_balance
    likelihood_sigma = weighted_std_dev if weighted_std_dev > 0 else prior_sigma
    n_games = effective_n_games  # Use effective sample size accounting for time weights
    
    if prior_sigma > 0 and likelihood_sigma > 0:
        prior_var = prior_sigma ** 2
        likelihood_var = likelihood_sigma ** 2
        posterior_var = 1 / ((1/prior_var) + (n_games/likelihood_var))
        posterior_mean = posterior_var * ((prior_mean/prior_var) + (n_games*likelihood_mean/likelihood_var))
        posterior_sigma = math.sqrt(posterior_var)
    else:
        posterior_mean = likelihood_mean
        posterior_sigma = likelihood_sigma
        
    pred_sigma = math.sqrt(posterior_sigma**2 + likelihood_sigma**2)
    
    if pred_sigma > 0:
        z_score = (0 - posterior_mean) / pred_sigma
        win_prob = 0.5 * (1 - math.erf(z_score / math.sqrt(2)))
    else:
        win_prob = 0.5 if posterior_mean == 0 else (1.0 if posterior_mean > 0 else 0.0)
        
    # Playstyle
    style_label = "Balanced"
    style_desc = "Average style"
    is_profitable = posterior_mean > 0
    is_volatile = False
    if avg_team_std_dev > 0:
        if (std_dev / avg_team_std_dev) >= 1.1:
            is_volatile = True
    else:
        is_volatile = std_dev > 150.0 # Fallback if no team data
    
    if is_profitable:
        if is_volatile:
            style_label = "Volatile Winner"
            style_desc = "Experiences high variance but maintains a positive win rate. Expect big swings."
        else:
            style_label = "Consistent Winner"
            style_desc = "Steady, reliable accumulation of profit with controlled risk."
    else:
        if is_volatile:
            style_label = "High Variance"
            style_desc = "Large swings in results with an overall negative trend. High risk."
        else:
            style_label = "Low Variance"
            style_desc = "Low risk, conservative results. Steady but slightly negative trend."

    # Reliability Score (0 to 100%)
    # We reach 100% confidence/reliability roughly at 30+ games (industry standard for rule of thumb)
    reliability = min(100, (n_games / 30) * 100)
    
    if n_games < 5:
        reliability_desc = "Low (Need more games)"
    elif n_games < 15:
        reliability_desc = "Moderate"
    else:
        reliability_desc = "High"

    adv_stats_bayesian = {
        "prior_mean": prior_mean,
        "prior_sigma": prior_sigma,
        "likelihood_mean": likelihood_mean,
        "likelihood_sigma": likelihood_sigma,
        "posterior_mean": posterior_mean,
        "posterior_sigma": posterior_sigma,
        "pred_sigma": pred_sigma,
        "win_prob": win_prob * 100,
        "expected_range_low": posterior_mean - 1.96 * pred_sigma,
        "expected_range_high": posterior_mean + 1.96 * pred_sigma,
        "style_label": style_label,
        "style_desc": style_desc,
        "reliability_score": reliability,
        "reliability_label": reliability_desc,
        "sample_size": games_count,  # Display actual number of games (integer)
        "effective_sample_size": n_games,  # Time-weighted effective sample size (float)
        "actual_std_dev": std_dev,
        "volatility_index": volatility_index,
        "team_avg_vol_idx": avg_team_vol_idx,
        "volatility_label": volatility_label,
        "avg_buyin": avg_buyin_val
    }

    # Consolidated Adv Stats for Template
    adv_stats = {
        "total_investment": total_investment,
        "avg_buyin": avg_buyin_val,
        "avg_balance": avg_balance,
        "attendance_pct": (games_count / team_total_games * 100) if team_total_games else 0,
        "attendance_count": games_count,
        "team_total_games": team_total_games,
        "total_balance": total_balance,
        "hourly_winrate": winrate,
        "roi": (total_balance / total_investment * 100) if total_investment else 0,
        "win_share_pct": player_metrics[player_id]["win_share"] if player_id in player_metrics else 0,
        "wins": wins_count,
        "draws": draws_count,
        "losses": losses_count,
        "win_pct": (wins_count / games_count * 100) if games_count else 0,
        "best_result": best_result,
        "worst_result": worst_result,
        "last_5_games": sorted(games_history, key=lambda x: (x["game"].date), reverse=True)[:5],
        "variance": variance if games_history else 0,
        "std_dev": std_dev if games_history else 0,
        "typical_range_low": avg_balance - std_dev if games_history else 0,
        "typical_range_high": avg_balance + std_dev if games_history else 0,
        "volatility_index": volatility_index,
        "volatility_label": volatility_label,
        "avg_team_vol_idx": avg_team_vol_idx,
        "avg_team_std_dev": avg_team_std_dev,
        "ranks": ranks,
        "team_avgs": adv_stats_team,
        "monthly_balances": sorted_months,
        "bayesian": adv_stats_bayesian,
    }

    # Sorting for Display
    reverse_order = order == "desc"
    if sort == "date":
        games_history.sort(key=lambda x: (x["game"].date, x["game"].start_time or datetime.min.time()), reverse=reverse_order)
    elif sort == "balance":
        games_history.sort(key=lambda x: x["balance"], reverse=reverse_order)
    elif sort == "pot":
        games_history.sort(key=lambda x: x["total_pot"], reverse=reverse_order)
    else:
        games_history.sort(key=lambda x: (x["game"].date), reverse=reverse_order)

    # Chart Data (Cumulative Balance)
    chart_data_src = sorted(games_history, key=lambda x: (x["game"].date, x["game"].start_time or datetime.min.time()))
    chart_points = []
    running_bal = 0.0
    for g in chart_data_src:
        running_bal += g["balance"]
        chart_points.append({
            "date": str(g["game"].date),
            "balance": running_bal
        })

    return {
        "request": request,
        "team": team,
        "player": player,
        "games_history": games_history,
        "adv_stats": adv_stats,
        "games_count": games_count,
        "total_balance": total_balance,
        "winrate": winrate,
        "available_years": available_years,
        "selected_year": year if year else "all",
        "chart_points": chart_points,
        "sort_by": sort,
        "order": order,
        "is_admin": is_admin,
        "player_role": player_role,
        "visible_count": len(games_history),
        "current_user": current_user,
    }


@router.post("/{team_id}/player/{player_id}/role")
async def change_player_role(
    request: Request,
    team_id: int,
    player_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user),
):
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if not is_user_admin(current_user.id, team.id, db):
        raise HTTPException(
            status_code=403, detail="Only admins can change roles"
        )

    if player_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="Cannot change your own role"
        )

    # Update role in UserTeam association
    user_team = (
        db.query(UserTeam)
        .filter(UserTeam.team_id == team_id, UserTeam.user_id == player_id)
        .one_or_none()
    )
    if not user_team:
        raise HTTPException(status_code=404, detail="Player not in group")

    from backend.db.models.team_role import TeamRole
    if role.upper() == "ADMIN":
        user_team.role = TeamRole.ADMIN
    else:
        user_team.role = TeamRole.MEMBER

    db.add(user_team)
    db.commit()

    return RedirectResponse(
        url=f"/team/{team_id}/player/{player_id}?msg=Role updated successfully",
        status_code=status.HTTP_303_SEE_OTHER,
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
    if not team or not is_user_admin(user.id, team.id, db):
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

    if not is_user_admin(user.id, team.id, db):
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

    if not is_user_admin(current_user.id, team.id, db):
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
            if not nick_name:
                return None
            if nick_name in team_users_map:
                return team_users_map[nick_name]

            # Create Guest User
            normalized_nick = unicodedata.normalize('NFD', nick_name.lower().replace('ł', 'l').replace('Ł', 'L'))
            ascii_nick = "".join(c for c in normalized_nick if unicodedata.category(c) != 'Mn').replace(' ', '_')
            new_email = f"{ascii_nick}_{team.search_code.lower()}@over-bet.com"

            player_user = User(
                email=new_email,
                nick=nick_name,
                hashed_password=Hasher.get_password_hash("guest123"),
                is_active=True,
            )
            db.add(player_user)
            db.commit()
            db.refresh(player_user)

            ut = UserTeam(
                user_id=player_user.id,
                team_id=team.id,
                status=PlayerRequestStatus.APPROVED,
            )
            db.add(ut)
            db.commit()

            team_users_map[nick_name] = player_user
            return player_user

        imported_count = 0
        skipped_count = 0

        for g_data in data:
            # 1. Parse Date/Time
            start_str = g_data.get("start_time")  # "YYYY-MM-DD HH:MM"
            finish_str = g_data.get("finish_time")  # "YYYY-MM-DD HH:MM"

            dt_start = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            dt_finish = datetime.strptime(finish_str, "%Y-%m-%d %H:%M")
            g_date = dt_start.date()

            # 2. Check Duplicates
            exists = (
                db.query(Game)
                .filter(Game.team_id == team.id, Game.start_time == dt_start)
                .first()
            )

            if exists:
                skipped_count += 1
                continue

            # 3. Determine Owner (Host)
            host_nick = g_data.get("host")
            # Any admin can be the "default" for game creation? 
            # Or just person who imports is the owner of those games.
            game_owner_id = current_user.id
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
                team_id=team.id,
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
                        time=dt_start,
                    )
                    db.add(bi)

                if cash_out_amt > 0:
                    co = CashOut(
                        amount=cash_out_amt,
                        user_id=player_user.id,
                        game_id=new_game.id,
                        time=dt_finish,
                        status=PlayerRequestStatus.APPROVED,
                    )
                    db.add(co)
                elif buy_in_amt > 0:
                    co = CashOut(
                        amount=0,
                        user_id=player_user.id,
                        game_id=new_game.id,
                        time=dt_finish,
                        status=PlayerRequestStatus.APPROVED,
                    )
                    db.add(co)

            db.commit()
            imported_count += 1

        msg = f"Imported {imported_count} games. Skipped {skipped_count} duplicates."
        return RedirectResponse(f"/team/{team_id}?msg={msg}", status_code=303)

    except Exception as e:
        # Check if json error
        return RedirectResponse(
            f"/team/{team_id}?errors=Import failed: {str(e)}", status_code=303
        )


@router.get("/{id}/stats", name="team_advanced_stats")
async def team_advanced_stats(
    request: Request,
    id: int,
    year: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id=id, db=db)
    if not team:
        return responses.RedirectResponse("/")

    stats = _calculate_team_stats(team, year, db)

    return templates.TemplateResponse(
        "team/team_stats.html", {"request": request, "team": team, "stats": stats}
    )


def _calculate_team_stats(team, year, db):
    # Filter games
    query = db.query(Game).filter(Game.team_id == team.id)
    if year and year != "all":
        query = query.filter(Game.date.like(f"{year}%"))
    games = query.all()



    games_count = len(games)

    # Host Stats (Owner)
    owners = [g.owner_id for g in games]
    from collections import Counter, defaultdict

    top_host_data = None
    if owners:
        host_counts = Counter(owners)
        top_host_id, top_host_count = host_counts.most_common(1)[0]
        top_host = db.query(User).filter(User.id == top_host_id).first()
        if top_host:
            top_host_data = {
                "nick": top_host.nick,
                "pct": (top_host_count / games_count * 100),
            }

    # Frequency
    sorted_dates = sorted([g.date for g in games])  # Strings YYYY-MM-DD
    frequency = "N/A"
    if games_count > 1:
        try:
            d1 = str(sorted_dates[0])[:10]
            d2 = str(sorted_dates[-1])[:10]
            from datetime import datetime

            first = datetime.strptime(d1, "%Y-%m-%d")
            last = datetime.strptime(d2, "%Y-%m-%d")
            days = (last - first).days
            if days > 0:
                val = days / (games_count - 1)
                frequency = f"{val:.1f}"
            else:
                frequency = "0.0"  # Multiple games same day
        except:
            pass

    # Players & Financials
    total_pot = 0
    total_players = 0

    player_profits = defaultdict(float)
    game_performances = []
    player_games_count = defaultdict(int)
    player_buyins = defaultdict(float)

    game_ids = [g.id for g in games]

    from backend.db.models.buy_in import BuyIn
    from backend.db.models.add_on import AddOn
    from backend.db.models.cash_out import CashOut

    avg_players = 0
    avg_pot = 0
    avg_buyin_all = 0
    avg_buyin_top10 = 0
    avg_win = 0
    avg_loss = 0
    rankings_profit = []
    sorted_w = []
    sorted_l = []
    most_volatile = []
    the_rocks = []

    if game_ids:
        bis = db.query(BuyIn).filter(BuyIn.game_id.in_(game_ids)).all()
        aos = (
            db.query(AddOn)
            .filter(
                AddOn.game_id.in_(game_ids),
                AddOn.status == PlayerRequestStatus.APPROVED,
            )
            .all()
        )
        cos = db.query(CashOut).filter(CashOut.game_id.in_(game_ids)).all()

        game_data = defaultdict(
            lambda: defaultdict(lambda: {"buyin": 0.0, "cashout": 0.0})
        )

        for b in bis:
            game_data[b.game_id][b.user_id]["buyin"] += b.amount
        for a in aos:
            game_data[a.game_id][a.user_id]["buyin"] += a.amount
        for c in cos:
            game_data[c.game_id][c.user_id]["cashout"] += c.amount

        positive_balances = []
        negative_balances = []
        total_entries = 0

        user_cache = {}

        def get_nick(uid):
            if uid not in user_cache:
                u = db.query(User).filter(User.id == uid).first()
                user_cache[uid] = u.nick if u else "Unknown"
            return user_cache[uid]

        for gid, players in game_data.items():
            g_obj = next((g for g in games if g.id == gid), None)
            g_date = str(g_obj.date) if g_obj else ""

            total_players += len(players)

            for uid, val in players.items():
                b = val["buyin"]
                c = val["cashout"]
                balance = c - b

                total_pot += b
                total_entries += 1

                player_profits[uid] += balance
                player_games_count[uid] += 1
                player_buyins[uid] += b

                nick = get_nick(uid)
                game_performances.append(
                    {"nick": nick, "value": balance, "date": g_date}
                )

                if balance > 0:
                    positive_balances.append(balance)
                if balance < 0:
                    negative_balances.append(balance)

        avg_players = total_players / games_count if games_count else 0
        avg_pot = total_pot / games_count if games_count else 0
        avg_buyin_all = total_pot / total_entries if total_entries else 0

        avg_win = (
            sum(positive_balances) / len(positive_balances) if positive_balances else 0
        )
        avg_loss = (
            sum(negative_balances) / len(negative_balances) if negative_balances else 0
        )

        # Top 10 Buyin
        top_10_players = sorted(
            player_games_count.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_10_ids = [x[0] for x in top_10_players]
        top_10_buyin_sum = sum(player_buyins[uid] for uid in top_10_ids)
        top_10_entries = sum(player_games_count[uid] for uid in top_10_ids)
        avg_buyin_top10 = top_10_buyin_sum / top_10_entries if top_10_entries else 0

        sorted_profit = sorted(player_profits.items(), key=lambda x: x[1], reverse=True)
        rankings_profit = [
            {"nick": get_nick(uid), "value": val} for uid, val in sorted_profit
        ]

        sorted_w = sorted(game_performances, key=lambda x: x["value"], reverse=True)
        sorted_l = sorted(game_performances, key=lambda x: x["value"])

        # Volatility Rankings (Absolute Standard Deviation)
        # Only include players with 15+ games (High Model Reliability)
        min_games = 15
        volatility_ranks = []
        import math

        for uid, count in player_games_count.items():
            if count >= min_games:
                # Get all balances for this player
                p_bals = []
                for gid, players in game_data.items():
                    if uid in players:
                        p_bals.append(players[uid]["cashout"] - players[uid]["buyin"])
                
                if len(p_bals) > 1:
                    mean = sum(p_bals) / len(p_bals)
                    variance = sum((x - mean) ** 2 for x in p_bals) / (len(p_bals) - 1)
                    sd = math.sqrt(variance)
                    volatility_ranks.append({"nick": get_nick(uid), "value": sd})

        most_volatile = sorted(volatility_ranks, key=lambda x: x["value"], reverse=True)
        the_rocks = sorted(volatility_ranks, key=lambda x: x["value"])

    stats = {
        "games_count": games_count,
        "avg_players": avg_players,
        "frequency": frequency,
        "top_host": top_host_data,
        "total_pot": total_pot,
        "avg_pot": avg_pot,
        "avg_buyin_all": avg_buyin_all,
        "avg_buyin_top10": avg_buyin_top10,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "rankings": {
            "profit": rankings_profit,
            "biggest_winner": sorted_w,
            "biggest_loser": sorted_l,
            "most_volatile": most_volatile,
            "rocks": the_rocks,
        },
    }
    return stats

@router.get("/{team_id}/manage_operators", name="get_manage_operators_list")
async def get_manage_operators_list(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if not is_user_admin(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get all members with their roles
    # We need a custom query or helper to get (User, Role)
    from backend.db.models.team_role import TeamRole
    members_with_roles = (
        db.query(User, UserTeam.role)
        .join(UserTeam)
        .filter(
            UserTeam.team_id == team.id,
            UserTeam.status == PlayerRequestStatus.APPROVED,
        )
        .all()
    )
    
    # Sort: Admins, Book Keepers, Members
    def role_priority(role):
        if role == TeamRole.ADMIN: return 0
        if role == TeamRole.BOOK_KEEPER: return 1
        return 2

    sorted_members = sorted(
        members_with_roles, 
        key=lambda x: (role_priority(x[1]), x[0].nick.lower())
    )

    return templates.TemplateResponse(
        "game/partials/manage_operators.html",
        {
            "request": request,
            "team": team,
            "members": sorted_members,
            "TeamRole": TeamRole
        },
    )


@router.post("/{team_id}/player/{player_id}/role", name="update_player_role")
async def update_player_role(
    team_id: int,
    player_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if not is_user_admin(current_user.id, team.id, db):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate role
    from backend.db.models.team_role import TeamRole
    if role not in [TeamRole.MEMBER, TeamRole.ADMIN, TeamRole.BOOK_KEEPER]:
         raise HTTPException(status_code=400, detail="Invalid role")

    # Create a helper or import it if created in repo
    from backend.db.repository.team import update_user_role
    update_user_role(team.id, player_id, role, db)

    return responses.Response(status_code=200, headers={"HX-Refresh": "true"})
