from pydantic import BaseModel, field_validator


class GameCreate(BaseModel):
    date: str
    default_buy_in: float
    running: bool
    team_id: str
    chip_structure_id: str

    @field_validator("default_buy_in")
    def ensure_correct_buyin(cls, value):
        if value < 0:
            raise ValueError(f"Buy-in should be positive number got {int(value)}")
        return value

    @field_validator("date")
    def ensure_correct_date(cls, value):
        if not value:
            raise ValueError("Failed to fill the date")
        return value

    @field_validator("chip_structure_id")
    def ensure_chip_structure_selected(cls, value):
        if not value:
            raise ValueError("Select chip structure")
        return value


class GameShow(BaseModel):
    id: str
    date: str
    running: bool
    team: str

    class Config:
        from_attributes = True
