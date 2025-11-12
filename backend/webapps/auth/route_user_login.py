import json

from fastapi import APIRouter, responses
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from backend.apis.v1.route_login import login_for_access_token
from backend.core.config import TEMPLATES_DIR
from backend.db.repository.user import create_new_user
from backend.db.session import get_db
from backend.schemas.user import UserCreate
from backend.webapps.auth.forms import LoginForm
from backend.webapps.user.forms import UserCreateForm

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/register/")
async def register_form(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register/")
async def register(request: Request, db: Session = Depends(get_db)):
    form = UserCreateForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            new_user_data = UserCreate(
                email=form.email,
                nick=form.nick,
                password=form.password,
            )
        except ValidationError as e:
            for error in json.loads(e.json()):
                form.errors.append(f"There is a problem with {error['loc'][0]}")
            return templates.TemplateResponse("auth/register.html", form.__dict__)

        try:
            new_user = create_new_user(user=new_user_data, db=db)

            # --- Auto-login after registration ---
            response = responses.RedirectResponse(
                "/", status_code=status.HTTP_302_FOUND
            )

            # Pass minimal login info to your token helper
            class TempLoginForm:
                username = new_user.email
                password = form.password

            login_for_access_token(response=response, form_data=TempLoginForm(), db=db)

            return response

        except IntegrityError:
            form.errors.append("User with that e-mail already exists.")
            return templates.TemplateResponse("auth/register.html", form.__dict__)

    return templates.TemplateResponse("auth/register.html", form.__dict__)


@router.post("/login/")
async def login(request: Request, db: Session = Depends(get_db)):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            form.__dict__.update(msg="Login Successful")
            response = responses.RedirectResponse(
                "/", status_code=status.HTTP_302_FOUND
            )
            login_for_access_token(response=response, form_data=form, db=db)
            return response
        except HTTPException:
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or password")
            return templates.TemplateResponse("auth/login.html", form.__dict__)
    return templates.TemplateResponse("auth/login.html", form.__dict__)


@router.get("/login/")
async def login(request: Request):
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
        },
    )


@router.post("/login/")
async def login(request: Request, db: Session = Depends(get_db)):
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            form.__dict__.update(msg="Login Successful")
            response = responses.RedirectResponse(
                "/", status_code=status.HTTP_302_FOUND
            )
            login_for_access_token(response=response, form_data=form, db=db)
            return response
        except HTTPException:
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or password")
            return templates.TemplateResponse("auth/login.html", form.__dict__)
    return templates.TemplateResponse("auth/login.html", form.__dict__)


@router.get("/logout/")
async def login(request: Request):
    response = responses.RedirectResponse(
        "/?msg=Successfully logged out", status_code=status.HTTP_302_FOUND
    )
    response.delete_cookie("access_token")

    return response
