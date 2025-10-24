import dataclasses
from typing import List, Optional, Type

from fastapi import Request
from pydantic import EmailStr
from starlette.datastructures import FormData


class UserCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.email: Optional[EmailStr] = None
        self.nick: Optional[str] = None
        self.password: Optional[str] = None
        self.repeat_password: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.nick = form.get("nick")
        self.email = form.get("email")
        self.password = form.get("password")
        self.repeat_password = form.get("repeat_password")

    async def is_valid(self):
        if not self.nick:
            self.errors.append("Nick is required")
        if not self.password or len(self.password) < 4:
            self.errors.append("Password needs to be at least 4 characters")
        if not self.email:
            self.errors.append("Wrong email address")
        if self.password != self.repeat_password:
            self.errors.append("Passwords don't match")
        return len(self.errors) == 0

