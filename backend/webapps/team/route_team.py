import json
from sqlite3 import IntegrityError
from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException, Form
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
from backend.db.repository.game import (
    get_user_games_count, 
    get_user_total_balance,
    get_user_team_games_count,
    get_user_team_balance,
    get_user_game_balance,
    get_user_team_games
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


@router.get("/{team_id}")
async def team_view(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return {"error": "Group not found"}

    join_requests = get_team_join_requests(team, db)
    players_info = []
    for player in get_team_approved_players(team, db):
        games_count = get_user_team_games_count(player, team.id, db)
        total_balance = get_user_team_balance(player, team.id, db)
        players_info.append(
            {
                "player": player,
                "games_count": games_count,
                "total_balance": total_balance,
            }
        )

    return templates.TemplateResponse(
        "team/team_view.html",
        {
            "request": request,
            "current_user": user,
            "team": team,
            "join_requests": join_requests,
            "players_info": players_info,
        },
    )


@router.get("/{team_id}/player/{player_id}")
async def player_stats(
    request: Request,
    team_id: int,
    player_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token),
):
    team = get_team_by_id(team_id, db)
    if not team:
        return RedirectResponse("/")

    # Verify user is in team
    if user not in team.users:
         return RedirectResponse("/")

    player = get_user(player_id, db)
    if not player:
        return RedirectResponse(f"/team/{team_id}")

    # Get games for this player IN THIS TEAM
    team_games = get_user_team_games(player, team_id, db)
    # Sort descending
    team_games.sort(key=lambda x: x.date, reverse=True)
    
    games_history = []
    
    for game in team_games:
        balance = get_user_game_balance(player, game, db)
        games_history.append({"game": game, "balance": balance})
    
    total_balance = sum(g["balance"] for g in games_history)

    return templates.TemplateResponse(
        "team/player_stats.html",
        {
            "request": request,
            "team": team,
            "player": player,
            "games_history": games_history,
            "total_balance": total_balance,
            "games_count": len(games_history),
            "is_owner": user.id == team.owner_id
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
