from typing import List, Optional, Type

from fastapi import Request


class TeamCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.name: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.name = form.get("name")

    async def is_valid(self):
        if not self.name:
            self.errors.append("Name is required")
        return len(self.errors) == 0
