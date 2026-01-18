from typing import Optional
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_core import PydanticCustomError


class AddOnRequest(BaseModel):
    add_on: float = 0.0

    @field_validator("add_on")
    def add_on_bigger_than_0(cls, value):
        if value < 0:
            raise PydanticCustomError(
                "add_on_lower_than_0", "Make sure add-on is bigger or equal to 0"
            )
        return value
