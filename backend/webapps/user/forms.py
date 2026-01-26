from typing import List, Optional
from backend.core.config import settings
from pydantic import BaseModel, field_validator
from email_validator import validate_email, EmailNotValidError

from fastapi import Request
from pydantic import EmailStr


class UserCreateForm(BaseModel):
    email: Optional[EmailStr] = None
    nick: Optional[str] = None
    password: Optional[str] = None
    repeat_password: Optional[str] = None

    @field_validator("nick")
    def is_nick_valid(cls, nick):
        if not nick:
            raise ValueError("Nick is required")
        if len(nick) < settings.NICK_LENGTH:
            raise ValueError(
                f"Nick needs to be at least {settings.NICK_LENGTH} characters"
            )
        return nick

    @field_validator("email")
    def is_email_valid(cls, email):
        if not email:
            raise ValueError("Email is required")
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            raise ValueError("Invalid email address")
        return email

    @field_validator("password")
    def is_password_valid(cls, password):
        if not password:
            raise ValueError("Password is required")
        if len(password) < settings.PASSWORD_LENGTH:
            raise ValueError(
                f"Password needs to be at least {settings.PASSWORD_LENGTH} characters"
            )
        return password

    @field_validator("repeat_password")
    def is_repeat_password_valid(cls, repeat_password):
        if not repeat_password:
            raise ValueError("Repeat password is required")
        if repeat_password != cls.password:
            raise ValueError("Passwords don't match")
        return repeat_password


class ResetPasswordForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.email: Optional[EmailStr] = None
        self.password: Optional[str] = None
        self.repeat_password: Optional[str] = None

    @field_validator("email")
    def is_email_valid(cls, email):
        if not email:
            raise ValueError("Email is required")
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            raise ValueError("Invalid email address")
        return email

    @field_validator("password")
    def is_password_valid(cls, password):
        if not password:
            raise ValueError("Password is required")
        if len(password) < settings.PASSWORD_LENGTH:
            raise ValueError(
                f"Password needs to be at least {settings.PASSWORD_LENGTH} characters"
            )
        return password

    @field_validator("repeat_password")
    def is_repeat_password_valid(cls, repeat_password):
        if not repeat_password:
            raise ValueError("Repeat password is required")
        if repeat_password != cls.password:
            raise ValueError("Passwords don't match")
        return repeat_password


class UserProfileForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.email: Optional[str] = None
        self.nick: Optional[str] = None
        self.password: Optional[str] = None
        self.repeat_password: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.email = form.get("email")
        self.nick = form.get("nick")
        self.password = form.get("password")
        self.repeat_password = form.get("repeat_password")

    async def is_valid(self):
        if not self.email:
             self.errors.append("Email is required")
        else:
             try:
                 validate_email(self.email, check_deliverability=False)
             except EmailNotValidError:
                 self.errors.append("Invalid email address")
             
        if not self.nick:
             self.errors.append("Nick is required")
        elif len(self.nick) < settings.NICK_LENGTH:
             self.errors.append(f"Nick needs to be at least {settings.NICK_LENGTH} characters")
             
        if self.password:
            if len(self.password) < settings.PASSWORD_LENGTH:
                self.errors.append(f"Password needs to be at least {settings.PASSWORD_LENGTH} characters")
            if self.password != self.repeat_password:
                self.errors.append("Passwords do not match")
                
        return not self.errors
             
        if not self.nick:
             self.errors.append("Nick is required")
        elif len(self.nick) < settings.NICK_LENGTH:
             self.errors.append(f"Nick needs to be at least {settings.NICK_LENGTH} characters")
             
        if self.password:
            if len(self.password) < settings.PASSWORD_LENGTH:
                self.errors.append(f"Password needs to be at least {settings.PASSWORD_LENGTH} characters")
            if self.password != self.repeat_password:
                self.errors.append("Passwords do not match")
                
        return not self.errors
