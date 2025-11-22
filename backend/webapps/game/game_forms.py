import dataclasses
from datetime import datetime
from typing import List, Optional, Type, Union

from fastapi import Request
from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

from backend.db.models.chip_amount import ChipAmount
from backend.schemas.chip_amount import ChipAmountCreate


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
                self.chips_amounts.append(
                    ChipAmountCreate(chip_id=chip["id"], amount=count)
                )

    async def is_valid(self):
        # Validation for total
        if self.amount is None or self.amount < 0:
            self.errors.append("Cash-out total must be 0 or more.")

        return len(self.errors) == 0


class CashOutByAmountRequest(BaseModel):
    amount: float = 0.0

    @field_validator("amount")
    def amount_bigger_than_0(cls, value):
        if value < 0:
            print("raising custom error")
            raise PydanticCustomError(
                "amount_lower_than_0", "Make sure amount is bigger or equal to 0"
            )
        return value
