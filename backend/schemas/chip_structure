from pydantic import BaseModel


class ChipStructureCreate(BaseModel):
    team_id: int
    game_id: int

class ChipStructureShow(BaseModel):
    id: str
    team_id: int
    game_id: int

    class Config:
        orm_mode = True