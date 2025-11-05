from pydantic import BaseModel

class ChipCreate(BaseModel):
    color_r: int
    color_g: int
    color_b: int
    value: float
    chip_structure_id: int


class NewChip(BaseModel):
    color_r: int
    color_g: int
    color_b: int
    value: float


class ChipShow(BaseModel):
    id: str
    color_r: int
    color_g: int
    color_b: int
    value: float
    chip_structure_id: int

    class Config:
        orm_mode = True
