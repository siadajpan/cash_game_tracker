from pydantic import BaseModel, validator


class ChipCreate(BaseModel):
    color_r: int
    color_g: int
    color_b: int
    value: float
    chip_structure_id: int

    @validator("value")
    def ensure_correct_value(cls, value):
        if value < 0:
            raise ValueError(f"Chip value should be positive number got {int(value)}")
        return value


class ChipShow(BaseModel):
    id: str
    color_r: int
    color_g: int
    color_b: int
    value: float
    chip_structure_id: int

    class Config:
        orm_mode = True
