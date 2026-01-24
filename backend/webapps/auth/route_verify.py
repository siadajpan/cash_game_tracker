from fastapi import APIRouter, responses
from fastapi import Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from backend.db.session import get_db
from backend.db.models.user_verification import UserVerification
from datetime import datetime
from backend.db.models.user import User
from fastapi_mail import FastMail, MessageSchema, MessageType
from backend.webapps.auth.email_config import conf
import asyncio
from backend.apis.v1.route_login import get_current_user
from backend.db.repository.user import create_verification_token
from backend.core.config import TEMPLATES_DIR
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from backend.core.config import settings
from backend.apis.v1.route_login import create_access_token, login_for_access_token
from backend.apis.v1.route_login import add_new_access_token
import resend

resend.api_key = settings.RESEND_API_KEY
router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


async def send_verification_email(email_to: str, nick: str, token: str):
    verification_url = f"{settings.URL}/verify?token={token}"
    template = templates.get_template("email/verify_email.html")
    html_content = template.render(nick=nick, link=verification_url)

    params = {
        "from": "Over-Bet <noreply@over-bet.com>",
        "to": [email_to],
        "subject": "Verify your Over-Bet account",
        "html": html_content,
    }

    try:
        resend.Emails.send(params)
    except Exception as e:
        print(f"Failed to send email: {e}")


@router.get("/verify-success")
async def verify_success(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "auth/verify_success.html", {"request": request, "user": user}
    )


@router.get("/verify-error")
async def verify_error(request: Request, can_resend: bool = False, error: str = ""):
    return templates.TemplateResponse(
        "auth/verify_error.html",
        {"request": request, "error": error, "can_resend": can_resend},
    )


@router.get("/verify")
async def verify_email(token: str, request: Request, db: Session = Depends(get_db)):
    # 1. Find the token in our new table
    verification = (
        db.query(UserVerification).filter(UserVerification.token == token).first()
    )

    if not verification:
        return await verify_error(
            request,
            can_resend=True,
            error="This link is invalid. Probably it was already used.",
        )

    # 2. Check if expired
    if datetime.utcnow() > verification.expires_at:
        db.delete(verification)
        db.commit()
        return await verify_error(
            request, can_resend=True, error="Your verification link has expired."
        )

    # 3. Mark user as active
    user = db.query(User).filter(User.id == verification.user_id).first()
    user.is_active = True

    # 4. Clean up: delete the verification record so the token can't be used again
    db.delete(verification)
    db.commit()

    response = await verify_success(request, user=user)
    response, access_token = add_new_access_token(response, user)

    return response


@router.get("/resend-verification")
async def resend_verification(
    request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # This assumes the user is logged in but is_active=False
    # If not logged in, you'd need a form to ask for their email
    user = get_current_user(request, db)
    print("current user", user)
    if not user:
        return RedirectResponse("/login")

    if user.is_active:
        print("user is active")
        return RedirectResponse(
            "/",
            status_code=status.HTTP_302_FOUND,
        )

    # 1. Delete any existing old tokens for this user
    db.query(UserVerification).filter(UserVerification.user_id == user.id).delete()

    # 2. Generate a brand new token
    new_token = create_verification_token(user.id, db)

    # 3. Send the email again
    background_tasks.add_task(send_verification_email, user.email, user.nick, new_token)

    return templates.TemplateResponse(
        "auth/verify_notice.html",
        {"request": request, "email": user.email, "nick": user.nick},
    )
