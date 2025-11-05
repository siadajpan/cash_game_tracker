
from turtle import color
from typing import List, Optional, Tuple

from fastapi import Request

from backend.schemas.chips import  NewChip




class ChipStructureCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List[str] = []
        self.team_id: Optional[int] = None
        self.created_by: Optional[int] = None
        self.chips: List[dict] = []

    async def load_data(self):
        form = await self.request.form()

        # Extract repeated chip fields
        chip_colors = form.getlist("color")
        chip_values = form.getlist("value")

        # Combine into structured list
        self.chips = []
        for color, value in zip(chip_colors, chip_values):
            if not color or not value:
                self.errors.append("Each chip must have a color and a value.")
                continue
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            self.chips.append(NewChip(color_r=r, color_g=g, color_b=b, value=value))
    
        # Basic fields
        self.team_id = form.get("team_id")
        self.created_by = form.get("created_by")

    async def is_valid(self):
        if not self.team_id:
            self.errors.append("Team ID is required.")
        if not self.chips:
            self.errors.append("At least one chip must be provided.")
        return len(self.errors) == 0
