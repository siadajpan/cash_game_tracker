
from turtle import color
from typing import List, Optional, Tuple

from anyio import value
from h11 import Request


class ChipForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.color_rgb: Optional[Tuple[int, int, int]] = None
        self.value: Optional[float] = None
        self.unit: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()

        # 1. Capture and validate the submitted chip value
        value = form.get("value")

        # If the submitted value is present and looks like a number, try to convert it.
        # If it's an empty string or "0" (which is invalid), leave it as None.
        try:
            if value and value.isdigit() and float(value) > 0:
                self.value = float(value)
            else:
                self.value = (
                    None  # Explicitly set to None if it's 0, empty, or invalid
                )
        except ValueError:
            self.errors.append("Chip value is invalid.")
            self.value = None
        
        color_r_str = form.get("color_r")
        color_g_str = form.get("color_g")   
        color_b_str = form.get("color_b")

        try:
            self.color_rgb = (
                int(color_r_str),
                int(color_g_str),
                int(color_b_str),
            )
        except (ValueError, TypeError):
            self.errors.append("Chip color is invalid.")
            self.color_rgb = None

    async def is_valid(self):
        # Validation for Chip Value
        if not self.value:
            self.errors.append("You must select a chip value.")

        # Validation for Chip Color
        if self.color_rgb is None:
            self.errors.append("Chip color must be valid.")

        return len(self.errors) == 0
