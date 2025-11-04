
from turtle import color
from typing import List, Optional, Tuple

from anyio import value
from h11 import Request

from backend.db.models.chip import Chip
from backend.schemas import chips


class ChipStructureCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.chips: Optional[Chip] = None

    async def load_data(self):
        form = await self.request.form()

        chips = form.get("chips")
        try:
            self.chips = chips
        except (ValueError, TypeError):
            self.errors.append("Chips are invalid.")
            self.chips = None

    async def is_valid(self):
        # Validation for Chip Value
        if not self.chips:
            self.errors.append("You must select a chip value.")

        return len(self.errors) == 0
