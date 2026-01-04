from typing import List, Optional
from backend.core.config import settings
from pydantic import BaseModel, field_validator

from fastapi import Request

from pydantic import EmailStr


class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    nick: Optional[str] = None
    password: Optional[str] = None
    repeat_password: Optional[str] = None

    @field_validator("nick")
    def is_nick_valid(cls, nick):
        if not nick:
            raise ValueError("Nick is required")
        if len(nick) < settings.NICK_LENGTH:
            raise ValueError(f"Nick needs to be at least {settings.NICK_LENGTH} characters")
        return nick

    @field_validator("email")
    def is_email_valid(cls, email):
        if not email:
            raise ValueError("Email is required")
        if not EmailStr._validate(email):
            raise ValueError("Invalid email address")
        return email

    @field_validator("password")
    def is_password_valid(cls, password):
        if not password:
            raise ValueError("Password is required")
        if len(password) < settings.PASSWORD_LENGTH:
            raise ValueError(f"Password needs to be at least {settings.PASSWORD_LENGTH} characters")
        return password

    @field_validator("repeat_password")
    def is_repeat_password_valid(cls, repeat_password):
        if not repeat_password:
            raise ValueError("Repeat password is required")
        if repeat_password != cls.password:
            raise ValueError("Passwords don't match")
        return repeat_password

  

class UserShow(BaseModel):
    id: int
    email: str
    nick: str

    class Config:
        from_attributes = True