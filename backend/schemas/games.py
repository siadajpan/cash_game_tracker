from typing import Optional
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_core import PydanticCustomError


class GameCreate(BaseModel):
    date: str
    default_buy_in: float
    running: bool
    team_id: str
    chip_structure_id: Optional[str]

    @field_validator("default_buy_in")
    def ensure_correct_buyin(cls, value):
        if value < 0:
            raise PydanticCustomError(
                "buyin_error",
                f"Default buy-in should be positive number got {int(value)}",
            )
        return value

    @field_validator("date")
    def ensure_correct_date(cls, value):
        if not value:
            raise AssertionError("Failed to fill the date")
        return value

    @field_validator("chip_structure_id")
    def ensure_chip_structure_selected(cls, value):
        if not value:
            raise PydanticCustomError(
                "chip_structure_error", "Select Chip Structure or create a new one"
            )
        return value


class GameJoin(BaseModel):
    buy_in: Optional[float] = None

    @field_validator("buy_in")
    def ensure_correct_buyin(cls, value):
        if value < 0:
            raise PydanticCustomError(
                "buy_in_negative",
                # Use a template string for the message
                "Buy-in must be a positive number. Got {value}",
                {"value": value},  # Context dictionary for the template
            )
        return value


class GameShow(BaseModel):
    id: str
    date: str
    running: bool
    team: str

    class Config:
        from_attributes = True
