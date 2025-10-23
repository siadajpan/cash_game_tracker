from typing import List, Optional

from fastapi import Request


class PatientCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.first_name: Optional[str] = None
        self.last_name: Optional[str] = None
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.repeat_password: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.first_name = form.get("first_name")
        self.last_name = form.get("last_name")
        self.email = form.get("email")
        self.password = form.get("password")
        self.repeat_password = form.get("repeat_password")

    async def is_valid(self):
        if not self.first_name:
            self.errors.append("First name is required.")
        if not self.last_name:
            self.errors.append("Last name is required.")
        if not self.password or len(self.password) < 4:
            self.errors.append("Password needs to be at least 4 characters.")
        if self.password != self.repeat_password:
            self.errors.append("Passwords don't match.")
        return len(self.errors) == 0
