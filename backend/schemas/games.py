from pydantic import BaseModel, validator


class GameCreate(BaseModel):
    date: str
    default_buy_in: float
    running: bool
    team_id: str

    @validator("default_buy_in")
    def ensure_correct_buyin(cls, value):
        if value < 0:
            raise ValueError(f"Buy-in should be positive number got {int(value)}")
        return value

    @validator("date")
    def ensure_correct_date(cls, value):
        if not value:
            raise ValueError("Failed to fill the date")
        return value


class GameShow(BaseModel):
    id: str
    date: str
    running: bool
    team: str

    class Config:
        orm_mode = True
