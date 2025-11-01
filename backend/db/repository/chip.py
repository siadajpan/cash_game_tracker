from typing import List, Type

from fastapi import Depends
from backend.db.models.chip import Chip
from backend.db.models.chip_structure import ChipStructure
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.session import get_db
from backend.schemas.chips import ChipStructureCreate, ChipCreate
from datetime import date


def create_new_chip(chip: ChipCreate,
                       current_user: User = Depends(get_current_user_from_token),
                       db: Session = Depends(get_db)):
    new_chip = Chip(
        owner_id=current_user.id,
        **chip.dict(),
    )
    # 2. Add the creator as a player (Many-to-Many)
    new_chip.players.append(current_user)

    db.add(new_chip)
    db.commit()
    db.refresh(new_chip)

    return new_chip


def retrieve_chip(chip_id: int, db: Session) -> Type[Chip]:
    item = db.get(Chip, chip_id)

    return item


def list_chips_in_structure(chip_structure_id: int, db: Session) -> List[Type[Chip]]:
    chips = db.query(Chip).filter(Chip.chip_structure_id == chip_structure_id).all()

    return chips

def edit_chip_value(chip_id: int, new_value: float, db: Session) -> Type[Chip]:
    chip = db.get(Chip, chip_id)
    chip.value = new_value

    db.commit()
    db.refresh(chip)

    return chip

