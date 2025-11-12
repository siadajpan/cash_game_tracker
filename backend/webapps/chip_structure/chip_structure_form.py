from turtle import color
from typing import List, Optional

from click import Option
from fastapi import Request

from backend.schemas.chips import NewChip


class ChipStructureCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List[str] = []
        self.team_id: Optional[int] = None
        self.created_by: Optional[int] = None
        self.chips: List[dict] = []
        self.name: Option[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.name = form.get("name")

        # Extract repeated chip fields
        chip_colors = form.getlist("color")
        chip_values = form.getlist("value")

        # Combine into structured list
        self.chips = []
        for color, value in zip(chip_colors, chip_values):
            if not color or not value:
                self.errors.append("Each chip must have a color and a value.")
                continue
            self.chips.append(NewChip(color=color, value=value))

        # Basic fields
        self.team_id = form.get("team_id")
        self.created_by = form.get("created_by")

    async def is_valid(self):
        if not self.team_id:
            self.errors.append("Team ID is required.")
        if not self.chips:
            self.errors.append("At least one chip must be provided.")
        return len(self.errors) == 0
