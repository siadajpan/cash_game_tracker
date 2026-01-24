from datetime import timedelta
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from backend.core.config import settings, TEMPLATES_DIR
from backend.db.session import get_db
from backend.db.models.team import Team
from backend.db.models.game import Game
from backend.db.repository.user import create_new_user
from backend.db.repository.team import join_team, get_team_by_id
from backend.db.repository.game import get_game_by_id, add_user_to_game
from backend.db.repository.buy_in import add_user_buy_in
from backend.schemas.user import UserCreate
from backend.apis.v1.route_login import add_new_access_token

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def verify_guest_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


@router.get("/join", name="guest_join_form")
async def guest_join_form(request: Request, token: str, db: Session = Depends(get_db)):
    payload = verify_guest_token(token)
    if not payload:
        return templates.TemplateResponse(
            "shared/error.html",
            {"request": request, "errors": ["Invalid or expired invitation link."]},
        )

    game_id = payload.get("game_id")
    game = get_game_by_id(game_id, db)
    if not game:
        return templates.TemplateResponse(
            "shared/error.html", {"request": request, "errors": ["Game not found."]}
        )

    if not game.running:
        return templates.TemplateResponse(
            "shared/error.html",
            {"request": request, "errors": ["This game has already finished."]},
        )

    return templates.TemplateResponse(
        "guest/join.html",
        {
            "request": request,
            "token": token,
            "game": game,
            "owner_nick": game.owner.nick if game.owner else "the host",
        },
    )


@router.post("/join", name="guest_join")
async def guest_join(
    request: Request,
    token: str = Form(...),
    nick: str = Form(...),
    db: Session = Depends(get_db),
):
    payload = verify_guest_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid token")

    game_id = payload.get("game_id")
    team_id = payload.get("team_id")

    game = get_game_by_id(game_id, db)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game.running:
        raise HTTPException(status_code=400, detail="This game has already finished")

    team = get_team_by_id(team_id, db)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Pre-load data to avoid DB access in error handler (which follows a failed session)
    owner_nick = game.owner.nick if game.owner else "the host"

    try:
        # 1. Create a guest user
        # Generate a random email and password since they are required fields
        random_suffix = str(uuid.uuid4())[:8]
        guest_email = f"guest_{random_suffix}@invitation.host"
        guest_password = str(uuid.uuid4())

        user_create = UserCreate(
            email=guest_email,
            nick=nick,
            password=guest_password,
            repeat_password=guest_password,
        )

        # Check if nick exists in this context? unique constraint is on email usually, but nick might need check.
        # For now relying on standard create.
        # NOTE: create_new_user might default is_active to False. We need to force it to True.

        new_user = create_new_user(user_create, db)
        # Force active since they are a guest joining via invite
        new_user.is_active = True
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # 2. Add to Team
        # Check if already in team? (Unlikely for new user)
        join_team(team, new_user, db)

        # 3. Log them in
        response = RedirectResponse(
            url=f"/game/{game_id}/join", status_code=status.HTTP_302_FOUND
        )
        response, _ = add_new_access_token(response, new_user)

        return response

    except Exception as e:
        print(f"Error in guest_join: {e}")  # Log to server console
        return templates.TemplateResponse(
            "guest/join.html",
            {
                "request": request,
                "token": token,
                "game": game,
                "owner_nick": owner_nick,  # Use pre-loaded string
                "errors": [f"Error joining game: {str(e)}"],
            },
        )
