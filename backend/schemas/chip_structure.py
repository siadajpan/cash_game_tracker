from pydantic import BaseModel

from backend.schemas.chips import NewChip


from typing import Optional

class ChipStructureCreate(BaseModel):
    name: str
    team_id: Optional[int] = None
    owner_id: Optional[int] = None
    chips: list[NewChip] = []


class ChipStructureShow(BaseModel):
    id: str
    team_id: Optional[int]
    owner_id: Optional[int]

    class Config:
        from_attributes = True
