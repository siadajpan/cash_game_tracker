from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user

from backend.apis.v1.route_login import get_current_user
from backend.core.config import TEMPLATES_DIR
from backend.db.session import get_db

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db), msg: str = None):
    # games = list_games_view(db=db)

    return templates.TemplateResponse(
        "general_pages/homepage.html",
        {
            "request": request,
            "msg": msg,
            "user": get_current_user(request, db)
        },
    )
