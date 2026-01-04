import json
from fastapi import BackgroundTasks
from fastapi import APIRouter, responses
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
import secrets
from backend.apis.v1.route_login import login_for_access_token
from backend.core.config import TEMPLATES_DIR
from backend.db.repository.user import (
    create_new_user,
    get_user_by_email,
    update_user_password,
)
from backend.db.session import get_db
from backend.schemas.user import UserCreate
from backend.webapps.auth.forms import LoginForm
from backend.webapps.user.forms import ResetPasswordForm, UserCreateForm
from backend.db.repository.user_verification import create_new_user_verification
from backend.webapps.auth.route_verify import send_verification_email
from backend.core.config import settings
from backend.apis.v1.route_login import create_access_token
from datetime import datetime, timedelta


templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/forgot-password/")
async def register_form(request: Request):
    return templates.TemplateResponse("auth/reset_password.html", {"request": request})


@router.post("/forgot-password/")
async def register(request: Request, db: Session = Depends(get_db)):
    form = ResetPasswordForm(request)
    await form.load_data()
    if not await form.is_valid():
        return templates.TemplateResponse("auth/reset_password.html", form.__dict__)

    try:
        user = get_user_by_email(form.email, db=db)
        if user is None:
            form.errors.append("User with that e-mail doesn't exist.")
            return templates.TemplateResponse("auth/reset_password.html", form.__dict__)
        update_user_password(user, form.password, db)
        # --- Auto-login after registration ---
        response = responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)

        # Pass minimal login info to your token helper
        class TempLoginForm:
            username = user.email
            password = form.password

        login_for_access_token(response=response, form_data=TempLoginForm(), db=db)

        return response

    except IntegrityError:
        form.errors.append("Unknown error")

    return templates.TemplateResponse("auth/reset_password.html", form.__dict__)


@router.get("/register/")
async def register_form(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register/")
async def register(
    request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    form = await request.form()
    errors = []
    try:
        # 1. Create User
        new_user_data = UserCreate(
            email=form.get("email"),
            nick=form.get("nick"),
            password=form.get("password"),
        )
        new_user = create_new_user(user=new_user_data, db=db)

        # 2. Create the response and SET THE COOKIE
        # This ensures the 'user' object is available in the next request
        response = responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)

        # We reuse your existing login helper to set the JWT cookie
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user.email}, expires_delta=access_token_expires
        )
        response.set_cookie(
            key="access_token", value=f"Bearer {access_token}", httponly=True
        )

        # 3. Create a UNIQUE verification token (Separate from the JWT)
        verif_token = secrets.token_urlsafe(32)
        create_new_user_verification(new_user.id, verif_token, db)

        # 4. Email the random token
        background_tasks.add_task(
            send_verification_email, new_user.email, new_user.nick, verif_token
        )

        return response

    except ValueError as e:
        errors.append(str(e))
    except IntegrityError as e:
        errors.append(f"User with that e-mail already exists.")
    except Exception as e:
        errors.append(f"Unexpected error: {e}")

    return templates.TemplateResponse(
        "auth/register.html", {"request": request, "form": form, "errors": errors}
    )


@router.post("/login/")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    errors = []
    try:
        form_data = LoginForm(username=form.get("email"), password=form.get("password"))

        response = responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        login_for_access_token(response=response, form_data=form_data, db=db)
        return response

    except ValidationError as e:
        # Catch Pydantic validation errors
        errors.extend([err["msg"] for err in e.errors()])
    except HTTPException:
        errors.append("Incorrect Email or password")

    return templates.TemplateResponse(
        "auth/login.html", {"request": request, "form": form, "errors": errors}
    )


@router.get("/login/")
async def login(request: Request):
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "form": {},
        },
    )


@router.get("/logout/")
async def login(request: Request):
    response = responses.RedirectResponse(
        "/?msg=Successfully logged out", status_code=status.HTTP_302_FOUND
    )
    response.delete_cookie("access_token")

    return response
