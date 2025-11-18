from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError


class GameCreate(BaseModel):
    model_config = ConfigDict(
        # This tells Pydantic to use the exception message directly
        # for assertion errors, overriding the default "Assertion failed, {msg}"
        error_msg_templates={
            "assertion_error": "{msg}",
        }
    )
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


class GameShow(BaseModel):
    id: str
    date: str
    running: bool
    team: str

    class Config:
        from_attributes = True
