from fastapi import APIRouter

from backend.apis.v1 import route_login
from backend.webapps import home
from backend.webapps.auth import route_user_login
from backend.webapps.chip_structure import route_chip_structure
from backend.webapps.game import route_game
from backend.webapps.team import route_team
from backend.webapps.user import route_user

api_router = APIRouter()
api_router.include_router(route_user.router, prefix="/user", tags=["user-webapp"])
api_router.include_router(home.router, prefix="", tags=["user-webapp"])
api_router.include_router(route_team.router, prefix="/team", tags=["team-webapp"])
api_router.include_router(route_game.router, prefix="/game", tags=["team-webapp"])
api_router.include_router(route_chip_structure.router, prefix="/chip_structure", tags=["team-webapp"])
api_router.include_router(route_login.router, prefix="", tags=["auth-webapp"])
api_router.include_router(route_user_login.router, prefix="", tags=["auth-webapp"])
