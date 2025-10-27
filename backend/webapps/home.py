from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user
from starlette.responses import RedirectResponse

from backend.apis.v1.route_login import get_current_user, get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.session import get_db

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(
    request: Request,
    user=Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
    msg: str = None,
):
    # games = list_games_view(db=db)

    if user is None:
        # Redirect to login page instead of rendering it here
        return RedirectResponse(url="/login", status_code=303)

    # Collect all running games from all user teams

    running_games = [g for t in user.teams for g in t.games if g.running]

    return templates.TemplateResponse(
        "general_pages/homepage.html",
        {
            "request": request,
            "msg": msg,
            "user": get_current_user(request, db),
            "running_games": running_games,
        },
    )
