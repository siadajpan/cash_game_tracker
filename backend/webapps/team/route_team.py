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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {"error": "Group not found"}

    from backend.db.repository.team import get_team_player_stats_bulk
    
    join_requests = get_team_join_requests(team, db)
    players_info = []
    
    # helper for bulk fetch
    bulk_stats = get_team_player_stats_bulk(team.id, db)
    
    for player in get_team_approved_players(team, db):
        p_stats = bulk_stats.get(player.id, {"games_count": 0, "total_balance": 0.0})
        
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
        },
    )


@router.get("/{team_id}/player/{player_id}")
async def player_stats(
    request: Request,
    team_id: int,
    player_id: int,
    sort: str = "date",
    order: str = "desc",
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
            # Check if game exists with same team, same start time (approx)
            exists = db.query(Game).filter(
                Game.team_id == team.id,
                Game.start_time == dt_start
            ).first()
            
            if exists:
                skipped_count += 1
                continue
                
            # 3. Create Game
            new_game = Game(
                date=g_date,
                start_time=dt_start,
                finish_time=dt_finish,
                default_buy_in=0,
                running=False,
                owner_id=team.owner_id,
                team_id=team.id
            )
            db.add(new_game)
            db.commit()
            db.refresh(new_game)
            
            # 4. Process Players
            players_list = g_data.get("players", [])
            for p_data in players_list:
                nick = p_data.get("nick")
                buy_in_amt = float(p_data.get("buy_in", 0))
                cash_out_amt = float(p_data.get("cash_out", 0))
                
                # Find User
                player_user = team_users_map.get(nick)
                
                if not player_user:
                    # Try finding global user by nick? Risky. 
                    # Create Guest User
                    random_suffix = secrets.token_hex(4)
                    new_email = f"{nick.lower().replace(' ', '_')}_{random_suffix}@imported.legacy"
                    
                    # Create user
                    player_user = User(
                        email=new_email,
                        nick=nick,
                        hashed_password=Hasher.get_password_hash("guest_imported"),
                        is_active=True
                    )
                    db.add(player_user)
                    db.commit()
                    db.refresh(player_user)
                    
                    # Add to Team
                    ut = UserTeam(
                        user_id=player_user.id,
                        team_id=team.id,
                        status=PlayerRequestStatus.APPROVED
                    )
                    db.add(ut)
                    db.commit()
                    
                    # Update cache
                    team_users_map[nick] = player_user
                
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
                    
                if cash_out_amt > 0: # Even if 0, record it? Usually yes, if played.
                    co = CashOut(
                        amount=cash_out_amt,
                        user_id=player_user.id,
                        game_id=new_game.id,
                        time=dt_finish,
                        status=PlayerRequestStatus.APPROVED
                    )
                    db.add(co)
                elif buy_in_amt > 0:
                    # If they bought in but no cashout record, assuming 0 cashout (lost everything)
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
