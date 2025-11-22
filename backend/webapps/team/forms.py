from typing import List, Optional, Type

from fastapi import Request
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError


class TeamCreateForm(BaseModel):
    name: Optional[str] = None

    @field_validator("name")
    def is_name_valid(cls, name):
        if not name:
            raise PydanticCustomError("name", "Name is required")
        return name


class TeamJoinForm(BaseModel):
    search_code: Optional[str] = None

    @field_validator("search_code")
    def check_search_code(cls, search_code):
        if len(search_code) < 4:
            raise PydanticCustomError(
                "search_code_too_short", "Please provide at least 4 digits"
            )
        return search_code
