from typing import List, Type

from fastapi import Depends
from backend.db.models.chip import Chip
from backend.db.models.chip_structure import ChipStructure
from backend.db.models.team import Team
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.db.models.game import Game
from backend.db.models.user import User
from backend.db.session import get_db
from backend.schemas.chips import ChipCreate
from backend.schemas.chip_structure import ChipStructureCreate
from datetime import date


def create_new_chip_structure_db(chips: List[ChipCreate],
                            team: Team,
                            db: Session = Depends(get_db)):
        new_chip_structure = ChipStructure(
            team_id=team.id
        )
        new_chips = [Chip(**chip.dict()) for chip in chips]
        new_chip_structure.chip = new_chips

        db.add(new_chip_structure)
        db.add_all(new_chips)
        db.commit()
        db.refresh(new_chip_structure)
    
        return new_chip_structure

def get_chip_structure(chip_structure_id: int, db: Session) -> Type[ChipStructure]:
    item = db.get(ChipStructure, chip_structure_id)

    return item

def list_team_chip_structures(team_id: int, db: Session) -> List[Type[ChipStructure]]:
    items = db.query(ChipStructure).filter(ChipStructure.team_id == team_id).all()

    return items

def add_team_chip_structure(team_id: int, chip_structure_id: int, db: Session) -> None:
    team = db.get(Team, team_id)
    chip_structure = db.get(ChipStructure, chip_structure_id)
    team.chip_structure = chip_structure

    db.add(team)
    db.commit()
    db.refresh(team)

def list_game_chip_structure(game_id: int, db: Session) -> Type[ChipStructure]:
    item = db.query(ChipStructure).filter(ChipStructure.game_id == game_id).one_or_none()

    return item

def add_chip_to_structure(chip_structure_id: int, chip: ChipCreate,
                          db: Session) -> Type[Chip]:
    new_chip = Chip(
        chip_structure_id=chip_structure_id,
        **chip.dict(),
    )

    db.add(new_chip)
    db.commit()
    db.refresh(new_chip)

    return new_chip

def remove_chip_from_structure(chip_id: int, db: Session) -> None:
    chip = db.get(Chip, chip_id)
    db.delete(chip)
    db.commit()

