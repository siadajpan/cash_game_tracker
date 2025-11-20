from typing import List
from typing import Optional
from unittest.mock import Base

from fastapi import Request
from pydantic import BaseModel, EmailStr, ValidationError, field_validator
from pydantic_core import PydanticCustomError


class LoginForm(BaseModel):
    username: Optional[EmailStr]
    password: Optional[str]

    @field_validator("username")
    def ensure_correct_username(cls, value):
        print(value)
        if "@" not in value:
            raise PydanticCustomError("email_error", "Email is required")
        return value

    @field_validator("password")
    def ensure_correct_password(cls, value):
        if not value or len(value) < 4:
            raise PydanticCustomError("pass_error", "A valid password is required")
        return value
