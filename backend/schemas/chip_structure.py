from pydantic import BaseModel

from backend.schemas.chips import NewChip


class ChipStructureCreate(BaseModel):
    name: str
    team_id: int
    chips: list[NewChip] = []


class ChipStructureShow(BaseModel):
    id: str
    team_id: int

    class Config:
        from_attributes = True
