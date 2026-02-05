from fastapi import APIRouter

from backend.apis.v1 import route_health, route_login
from backend.webapps import home
from backend.webapps.auth import route_user_login
from backend.webapps.chip_structure import route_chip_structure
from backend.webapps.game import route_game
from backend.webapps.game import route_game_cash_out
from backend.webapps.game import route_game_add_on
from backend.webapps.team import route_team
from backend.webapps.user import route_user
from backend.webapps.auth import route_verify

api_router = APIRouter()
api_router.include_router(route_user.router, prefix="/user", tags=["user-webapp"])
api_router.include_router(home.router, prefix="", tags=["user-webapp"])
api_router.include_router(route_health.health_router, prefix="")

api_router.include_router(route_team.router, prefix="/team", tags=["team-webapp"])
api_router.include_router(
    route_chip_structure.router, prefix="/chip_structure", tags=["team-webapp"]
)
api_router.include_router(route_game.router, prefix="/game", tags=["game-webapp"])
api_router.include_router(
    route_game_cash_out.router, prefix="/game", tags=["game-webapp"]
)
api_router.include_router(
    route_game_add_on.router, prefix="/game", tags=["game-webapp"]
)
from backend.webapps.game import route_game_history
from backend.webapps.game import route_predictions
api_router.include_router(
    route_game_history.router, prefix="/game", tags=["game-webapp"]
)
api_router.include_router(
    route_predictions.router, prefix="/game", tags=["game-webapp"]
)

api_router.include_router(route_login.router, prefix="", tags=["auth-webapp"])
api_router.include_router(route_user_login.router, prefix="", tags=["auth-webapp"])
api_router.include_router(route_verify.router, prefix="", tags=["auth-webapp"])
