from sqlalchemy.orm import Session

from backend.core.hashing import Hasher
from backend.db.models.user import User
from backend.schemas.user import UserCreate
import secrets
from datetime import datetime, timedelta
from backend.db.models.user_verification import UserVerification


def create_new_user_verification(user_id: int, access_token: str, db: Session):
    user_verification = UserVerification(
        user_id=user_id,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=1),
        token=access_token,
    )
    db.add(user_verification)
    db.commit()
