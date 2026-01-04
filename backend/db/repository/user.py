from sqlalchemy.orm import Session

from backend.core.hashing import Hasher
from backend.db.models.user import User
from backend.schemas.user import UserCreate
import secrets
from datetime import datetime, timedelta
from backend.db.models.user_verification import UserVerification


def create_new_user(user: UserCreate, db: Session):
    new_user = User(
        email=user.email,
        hashed_password=Hasher.get_password_hash(user.password),
        nick=user.nick,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def get_user_by_email(email: str, db: Session):
    user = db.query(User).filter(User.email == email).one_or_none()
    return user


def update_user_password(user, new_password, db: Session):
    hashed_password = Hasher.get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return user


def create_verification_token(db: Session, user_id: int):
    # 1. Generate a secure random string
    token = secrets.token_urlsafe(32)

    # 2. Set expiration (e.g., 24 hours from now)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    # 3. Save to the new table
    db_verification = UserVerification(
        user_id=user_id, token=token, expires_at=expires_at
    )

    db.add(db_verification)
    db.commit()
    return token
