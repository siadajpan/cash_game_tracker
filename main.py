import time
from pathlib import Path

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from backend.apis.base import api_router
from backend.core.config import settings
from backend.db.base import Base
from backend.db.models.player_request_status import PlayerRequestStatusEnum
from backend.db.session import engine
from backend.webapps.base import api_router as web_app_router
from sqlalchemy.exc import OperationalError


def include_router(app):
    app.include_router(api_router)
    app.include_router(web_app_router)


def configure_static(app):
    BASE_DIR = Path(__file__).resolve().parent
    STATIC_DIR = BASE_DIR / "backend/static"
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def create_tables():
    Base.metadata.create_all(bind=engine)

def create_enums(engine): 
    PlayerRequestStatusEnum.create(bind=engine, checkfirst=True)

def wait_for_db(engine, retries=10, delay=2): 
    for i in range(retries): 
        try: 
            with engine.connect() as conn: 
                print("Database is ready!") 
                return True 
        except OperationalError: 
            print(f"Database not ready, retrying {i+1}/{retries}...") 
            time.sleep(delay) 
    raise Exception("Database not available after retries")


def start_application():
    app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
    include_router(app)
    configure_static(app)
    wait_for_db(engine) 
    create_enums(engine)
    create_tables()

    return app


app = start_application()


@app.middleware("http")
async def redirect_unauthorized_to_login(request: Request, call_next):
    response = await call_next(request)

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        # Only redirect for HTML requests, not API calls
        if request.url.path.startswith("/api"):
            return response
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return response
