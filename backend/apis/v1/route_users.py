from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.repository.user import create_new_user, get_user_by_nick_id
from backend.db.session import get_db
from backend.schemas.user import UserCreate

router = APIRouter()


@router.post("/create")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    user = create_new_user(user=user, db=db)
    return user


@router.get("/get/{nick_id}")
def get_user(nick_id: str, db: Session = Depends(get_db)):
    user = get_user_by_nick_id(nick_id, db)
    return user
