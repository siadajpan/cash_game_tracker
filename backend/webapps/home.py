from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.db.session import get_db

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db), msg: str = None):
    # games = list_games_view(db=db)

    return templates.TemplateResponse(
        "general_pages/homepage.html",
        {
            "request": request,
            #"games": games,
            "msg": msg,
        },
    )
