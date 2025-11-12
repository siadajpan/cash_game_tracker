import dataclasses
from datetime import datetime
from typing import List, Optional, Type, Union

from fastapi import Request

from backend.db.models.chip_amount import ChipAmount
from backend.schemas.chip_amount import ChipAmountCreate


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
                self.team_id = (
                    None  # Explicitly set to None if it's 0, empty, or invalid
                )
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


class GameJoinForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.buy_in: Optional[float] = None

    async def load_data(self):
        form = await self.request.form()

        buy_in_str = form.get("buy_in")
        try:
            self.buy_in = float(buy_in_str) if buy_in_str else 0.0
        except ValueError:
            self.errors.append("Buy-in must be a valid number.")

    async def is_valid(self):
        # Validation for Default Buy-In
        if self.buy_in is None or self.buy_in < 0:
            self.errors.append("Buy-in must be a 0 or more.")

        return len(self.errors) == 0


class AddOnRequest:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.amount: float = 0.0

    async def load_data(self):
        form = await self.request.form()

        add_in_str = form.get("add_on")
        try:
            self.amount = float(add_in_str)
        except ValueError:
            self.errors.append("Add-on be a valid number.")

    async def is_valid(self):
        # Validation for Default Buy-In
        if self.amount is None or self.amount <= 0:
            self.errors.append("Add-on needs to be a positive number.")

        return len(self.errors) == 0

class CashOutRequest:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List[str] = []
        self.amount: float = 0.0
        self.chips_amounts: List[ChipAmountCreate] = []

    async def load_data(self, chip_structure: List):
        """
        Load total cash-out amount and per-chip quantities from form.
        `chip_structure` should be a list of Chip objects (in display order).
        """
        form = await self.request.form()

        # Total value
        cash_out = form.get("totalValue")
        try:
            self.amount = float(cash_out)
        except (ValueError, TypeError):
            self.errors.append("Cash-out amount must be a valid number.")
            self.amount = 0.0

        # Load chip counts
        self.chips_amounts = []
        for idx, chip in enumerate(chip_structure, start=1):
            key = f"chip_{idx}"
            count_str = form.get(key, "0")

            try:
                count = int(count_str)
                if count < 0:
                    raise ValueError
            except ValueError:
                self.errors.append(f"Invalid count for chip with value {chip['value']}")
                count = 0

            # only store nonzero chips
            if count > 0:
                self.chips_amounts.append(ChipAmountCreate(chip_id=chip['id'], amount=count))

    async def is_valid(self):
        # Validation for total
        if self.amount is None or self.amount < 0:
            self.errors.append("Cash-out total must be 0 or more.")

        return len(self.errors) == 0