import json
import requests
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
from backend.webapps.user.forms import ResetPasswordForm
from backend.webapps.auth.route_verify import send_verification_email
from backend.core.config import settings
from backend.apis.v1.route_login import create_access_token
from datetime import timedelta
from backend.db.repository.user import create_verification_token
from backend.apis.v1.route_login import add_new_access_token

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
        response = responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)

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
        new_user_data = UserCreate(
            email=form.get("email"),
            nick=form.get("nick"),
            password=form.get("password"),
        )
        
        if not form.get("tos_agreement"):
             raise ValueError("You must agree to the Terms of Service to register.")

        new_user = create_new_user(user=new_user_data, db=db)
        verif_token = create_verification_token(new_user.id, db)
        background_tasks.add_task(
            send_verification_email, new_user.email, new_user.nick, verif_token
        )

        response = templates.TemplateResponse(
            "auth/verify_notice.html",
            {"request": request, "email": new_user.email, "nick": new_user.nick},
        )
        response, access_token = add_new_access_token(response, new_user)
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


@router.get("/login/google")
async def login_google():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
        return responses.RedirectResponse(
            "/?msg=Google Login is not configured (missing credentials)",
            status_code=status.HTTP_302_FOUND
        )

    return responses.RedirectResponse(
        f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
    )


@router.get("/auth/google/callback")
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    if not code:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "errors": ["Login failed: No authorization code received"]},
        )

    try:
        # 1. Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        res = requests.post(token_url, data=data)
        res.raise_for_status()
        access_token = res.json().get("access_token")

        # 2. Get user info
        user_info_res = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_info_res.raise_for_status()
        user_info = user_info_res.json()
        
        email = user_info.get("email")
        if not email:
             raise ValueError("Google did not return an email address.")

        # 3. Check if user exists
        user = get_user_by_email(email, db)
        
        if not user:
            # Create a temporary token containing the email to secure the next step
            # We can reuse create_access_token but with a short expiry and specific scope/purpose if needed
            # For simplicity, we use the same structure but maybe a different subject prefix or just the email
            reg_token_expires = timedelta(minutes=15)
            reg_token = create_access_token(
                data={"sub": f"google_reg:{email}", "email": email, "suggested_nick": user_info.get("name") or email.split("@")[0]},
                expires_delta=reg_token_expires
            )
            
            return templates.TemplateResponse(
                "auth/finish_google_login.html",
                {
                    "request": request,
                    "email": email,
                    "suggested_nick": user_info.get("name") or email.split("@")[0],
                    "token": reg_token
                }
            )

        # 4. Login user (create access token)
        response = responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        response.set_cookie(
            key="access_token", value=f"Bearer {access_token}", httponly=True
        )
        
        return response

    except Exception as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "errors": [f"Google Login failed: {str(e)}"],
            },
        )


@router.post("/register/google/finish")
async def finish_google_registration(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    token = form.get("token")
    nick = form.get("nick")
    tos_agreement = form.get("tos_agreement")
    
    if not tos_agreement:
         return templates.TemplateResponse(
            "auth/finish_google_login.html",
            {
                "request": request,
                "error": "You must agree to the Terms of Service.",
                "token": token,
                "suggested_nick": nick
            }
        )

    try:
        # Decode token to get email
        # We need to import jwt and settings to decode
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("email")
        sub = payload.get("sub")
        
        if not email or not sub or not sub.startswith("google_reg:"):
            raise ValueError("Invalid registration token")
            
        # Create user
        random_password = secrets.token_urlsafe(16)
        new_user_data = UserCreate(
            email=email,
            nick=nick,
            password=random_password
        )
        user = create_new_user(user=new_user_data, db=db)
        user.is_active = True
        db.commit()
        
        # Login
        response = responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        response.set_cookie(
            key="access_token", value=f"Bearer {access_token}", httponly=True
        )
        return response

    except Exception as e:
         return templates.TemplateResponse(
            "auth/finish_google_login.html",
            {
                "request": request,
                "errors": [f"Registration failed: {str(e)}"],
                "token": token,
                 "suggested_nick": nick
            }
        )


@router.get("/logout/")
async def login(request: Request):
    response = responses.RedirectResponse(
        "/?msg=Successfully logged out", status_code=status.HTTP_302_FOUND
    )
    response.delete_cookie("access_token")

    return response
