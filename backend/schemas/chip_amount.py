from pydantic import BaseModel


class ChipAmountCreate(BaseModel):
    chip_id: int
    amount: int


class NewChipAmount(BaseModel):
    amount: int


class ChipShow(BaseModel):
    id: str
    color: str
    value: float
    chip_structure_id: int

    class Config:
        from_attributes = True
