from sqlalchemy.orm import Session

from backend.core.hashing import Hasher
from backend.db.models.user import User
from backend.schemas.user import UserCreate
import secrets
from datetime import datetime, timedelta
from backend.db.models.user_verification import UserVerification


def create_new_user(user: UserCreate, db: Session):
    new_user = User(
        nick_id=user.nick_id,
        hashed_password=Hasher.get_password_hash(user.password),
        nick=user.nick,
        is_active=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def get_user_by_nick_id(nick_id: str, db: Session):
    user = db.query(User).filter(User.nick_id == nick_id).one_or_none()
    return user


def get_user_by_login(login: str, db: Session):
    user = db.query(User).filter(User.nick_id == login).first()
    if not user:
        user = db.query(User).filter(User.nick == login).first()
    return user


def update_user_password(user, new_password, db: Session):
    hashed_password = Hasher.get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.commit()
    db.refresh(user)
    return user


def create_verification_token(user_id: int, db: Session):
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
