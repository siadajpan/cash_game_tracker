from fastapi import APIRouter

from backend.webapps import home
from backend.webapps.user import route_users
from backend.webapps.practices import route_practices
from webapps.auth import route_login

api_router = APIRouter()
api_router.include_router(
    route_doctors.router, prefix="/user", tags=["user-webapp"]
)
api_router.include_router(home.router, prefix="", tags=["user-webapp"])
api_router.include_router(
    route_practices.router, prefix="/practices", tags=["practices-webapp"]
)
api_router.include_router(
    route_login.router, prefix="", tags=["auth-webapp"]
)
