from fastapi import APIRouter

from backend.apis.v1 import (
    route_login,
    route_users,
)

api_router = APIRouter()
api_router.include_router(route_users.router, prefix="/users", tags=["users"])

api_router.include_router(route_login.router, prefix="/login", tags=["login"])
