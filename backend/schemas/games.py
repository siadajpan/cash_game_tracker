from pydantic import BaseModel, validator


class GameCreate(BaseModel):
    date: str
    default_buy_in: str

    @validator("default_buy_in")
    def ensure_correct_buyin(cls, value):
        if not str.isnumeric(value) or int(value) < 0:
            raise ValueError("Buy-in should be positive number")
        return value

class GameShow(BaseModel):
    id: str
    date: str

    class Config:
        orm_mode = True
