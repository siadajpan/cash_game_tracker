from fastapi import APIRouter, responses
from fastapi import Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from starlette import status

from backend.db.session import get_db
from backend.db.models.user_verification import UserVerification
from datetime import datetime
from backend.db.models.user import User
from fastapi_mail import FastMail, MessageSchema, MessageType
from backend.webapps.auth.email_config import conf
from backend.db.repository.user_verification import create_new_user_verification
import asyncio
from backend.apis.v1.route_login import get_current_user

router = APIRouter(include_in_schema=False)


async def send_verification_email(email_to: str, nick: str, token: str):
    verification_url = f"http://localhost:8000/verify?token={token}"
    template_data = {"nick": nick, "link": verification_url}

    message = MessageSchema(
        subject="Verify your Over-Bet account",
        recipients=[email_to],
        template_body=template_data,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name="verify_email.html")


@router.get("/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    # 1. Find the token in our new table
    verification = (
        db.query(UserVerification).filter(UserVerification.token == token).first()
    )

    if not verification:
        return responses.RedirectResponse(
            "/", status_code=status.HTTP_302_FOUND, message="Invalid token"
        )

    # 2. Check if expired
    if datetime.utcnow() > verification.expires_at:
        db.delete(verification)
        db.commit()
        return responses.RedirectResponse(
            "/",
            status_code=status.HTTP_302_FOUND,
            message="Token expired. Please request a new one.",
        )

    # 3. Mark user as active
    user = db.query(User).filter(User.id == verification.user_id).first()
    user.is_active = True

    # 4. Clean up: delete the verification record so the token can't be used again
    db.delete(verification)
    db.commit()

    return responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@router.get("/resend-verification")
async def resend_verification(
    request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # This assumes the user is logged in but is_active=False
    # If not logged in, you'd need a form to ask for their email
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse("/login")

    # Pass minimal login info to your token helper
    class TempLoginForm:
        username = user.email
        password = user.password

    token = login_for_access_token(response=response, form_data=TempLoginForm(), db=db)
    access_token = token["access_token"]

    if user.is_active:
        return responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    # 1. Delete any existing old tokens for this user
    db.query(UserVerification).filter(UserVerification.user_id == user.id).delete()

    # 2. Generate a brand new token
    create_new_user_verification(user.id, access_token, db)

    # 3. Send the email again
    background_tasks.add_task(send_verification_email, user.email, user.nick, new_token)

    return responses.RedirectResponse("/", status_code=status.HTTP_302_FOUND)
