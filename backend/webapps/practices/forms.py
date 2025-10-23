from typing import List, Optional

from fastapi import Request


class PracticeCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.repeat_password: Optional[str] = None
        self.name: Optional[str] = None
        self.postcode: Optional[str] = None
        self.city: Optional[str] = None
        self.address: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.email = form.get("email")
        self.password = form.get("password")
        self.repeat_password = form.get("repeat_password")
        self.name = form.get("name")
        self.postcode = form.get("postcode")
        self.city = form.get("city")
        self.address = form.get("address")

    async def is_valid(self):
        if not self.password or len(self.password) < 4:
            self.errors.append("Password needs to be at least 4 characters")
        if self.password != self.repeat_password:
            self.errors.append("Passwords don't match")
        return len(self.errors) == 0
