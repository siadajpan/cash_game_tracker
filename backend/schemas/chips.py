from pydantic import BaseModel


class ChipCreate(BaseModel):
    color: str
    value: float
    chip_structure_id: int


class NewChip(BaseModel):
    color: str
    value: float


class ChipShow(BaseModel):
    id: str
    color: str
    value: float
    chip_structure_id: int

    class Config:
        from_attributes = True
