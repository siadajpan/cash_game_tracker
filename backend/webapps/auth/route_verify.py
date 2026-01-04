from fastapi import APIRouter, responses
from fastapi import Depends
from sqlalchemy.orm import Session
from starlette import status

from backend.db.session import get_db
from backend.db.models.user_verification import UserVerification
from datetime import datetime
from backend.db.models.user import User

router = APIRouter(include_in_schema=False)
from fastapi_mail import FastMail, MessageSchema, MessageType
from backend.webapps.auth.email_config import conf

import asyncio


async def send_verification_email(email_to: str, nick: str, token: str):
    verification_url = f"https://over-bet.com/auth/verify?token={token}"
    print("sending email")
    # Data to be injected into the HTML template
    template_data = {"nick": nick, "link": verification_url}

    message = MessageSchema(
        subject="Verify your Over-Bet account",
        recipients=[email_to],
        template_body=template_data,  # Use this for HTML templates
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    # The 'template_name' refers to the filename inside your TEMPLATE_FOLDER
    await fm.send_message(message, template_name="verify_email.html")


@router.get("/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    # 1. Find the token in our new table
    verification = (
        db.query(UserVerification).filter(UserVerification.token == token).first()
    )

    if not verification:
        return {"error": "Invalid token"}

    # 2. Check if expired
    if datetime.utcnow() > verification.expires_at:
        db.delete(verification)
        db.commit()
        return {"error": "Token expired. Please request a new one."}

    # 3. Mark user as active
    user = db.query(User).filter(User.id == verification.user_id).first()
    user.is_active = True

    # 4. Clean up: delete the verification record so the token can't be used again
    db.delete(verification)
    db.commit()

    return {"message": "Email verified successfully! You can now log in."}


async def test_send():
    email_to = "forkarolm@gmail.com"
    nick = "karol"
    token = "123456"
    verification_url = f"http://localhost:8000/auth/verify?token={token}"

    print(f"Attempting to send email to {email_to}...")

    template_data = {"nick": nick, "link": verification_url}

    message = MessageSchema(
        subject="Verify your Over-Bet account",
        recipients=[email_to],
        template_body=template_data,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message, template_name="verify_email.html")
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


if __name__ == "__main__":
    # This is the standard way to run an async function in a script
    asyncio.run(test_send())
