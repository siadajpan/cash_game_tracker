import dataclasses
from datetime import datetime
from typing import List, Optional, Type, Union

from fastapi import Request

class GameCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.date: Optional[str] = None
        self.default_buy_in: Optional[float] = None
        self.team_id: Optional[Union[str, int]] = None

    async def load_data(self):
        form = await self.request.form()

        # 1. Capture and validate the submitted team ID
        team_id_str = form.get("team_id")

        # If the submitted value is present and looks like a number, try to convert it.
        # If it's an empty string or "0" (which is invalid), leave it as None.
        try:
            if team_id_str and team_id_str.isdigit() and int(team_id_str) > 0:
                self.team_id = int(team_id_str)
            else:
                self.team_id = None # Explicitly set to None if it's 0, empty, or invalid
        except ValueError:
            self.errors.append("Team selection ID is invalid.")
            self.team_id = None


        # 2. Capture and convert default buy-in
        buy_in_str = form.get("default_buy_in")
        try:
            self.default_buy_in = float(buy_in_str) if buy_in_str else 0.0
        except ValueError:
            self.errors.append("Default buy-in must be a valid number.")

        # 3. Capture date
        self.date = form.get("date", self.date)


    async def is_valid(self):
        # Validation for Team ID
        if not self.team_id:
            self.errors.append("You must select a team to create a game.")

        # Validation for Default Buy-In
        if self.default_buy_in is None or self.default_buy_in < 0:
            self.errors.append("Default buy-in must be 0 or more.")

        # Additional checks can go here...

        return len(self.errors) == 0
