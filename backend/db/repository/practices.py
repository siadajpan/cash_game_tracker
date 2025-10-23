from typing import List, Type

from sqlalchemy.orm import Session

from backend.db.models.practices import Practice
from backend.db.repository.users import create_new_user
from backend.schemas.practices import PracticeCreate
from backend.schemas.users import UserCreate


def create_new_practice(practice: PracticeCreate, db: Session):
    new_user = create_new_user(
        UserCreate(email=practice.email, password=practice.password), db
    )

    del practice.email
    del practice.password

    new_practice = Practice(
        user_id=new_user.id,
        **practice.dict(),
        descriptor=f"{practice.name}.{practice.city}.{practice.address}",
    )
    db.add(new_practice)
    db.commit()
    db.refresh(new_practice)

    return new_practice


def retrieve_practice(practice_id: int, db: Session) -> Type[Practice]:
    item = db.get(Practice, practice_id)

    return item


def list_practices(db: Session) -> List[Type[Practice]]:
    practices = db.query(Practice).all()

    return practices
