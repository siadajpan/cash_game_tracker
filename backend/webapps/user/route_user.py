from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models.user import User
from backend.schemas.user import UserShow


router = APIRouter(include_in_schema=False)

@router.get("/list", response_model=List[UserShow])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
