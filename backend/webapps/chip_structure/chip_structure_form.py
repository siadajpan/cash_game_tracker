from typing import Any, List, Optional

from fastapi import Request
from pydantic import BaseModel, field_validator, model_validator

from backend.schemas.chips import NewChip
from pydantic_core import PydanticCustomError


class ChipStructureCreateForm(BaseModel):
    team_id: Optional[int] = None
    created_by: Optional[int] = None
    chips: List[NewChip] = []
    name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def process_form_data(cls, data: Any) -> Any:
        """
        Parses raw form data (formdata) containing color/value lists
        and transforms it into the structured 'chips' field.
        This runs *before* field-level validators.
        """
        if not isinstance(data, dict):
            # This handles cases where data might not be a dictionary yet.
            # However, for manual instantiation, it will always be a dict.
            return data

        # Extract the list fields from the raw input dictionary (the form data)
        chip_colors = data.get("color", [])
        chip_values = data.get("value", [])

        if not chip_colors and not chip_values:
            # If no chip data is submitted, skip complex parsing
            return data

        chips_list = []

        # This is where your read_chips logic moves:
        for color, value in zip(chip_colors, chip_values):
            if not color or not value:
                raise PydanticCustomError(
                    "chip_color_error", "Each chip must have a color and a value."
                )
            
            chip_value = float(value)
            

            # Note: We let the NewChip sub-model validation handle the positive check,
            # or you can enforce it here again:
            if chip_value <= 0:
                raise PydanticCustomError(
                    "chip_value_error", "Chip value must be a positive number."
                )

            # Append the structured data. Pydantic will convert this dict
            # into a NewChip object during model creation.
            chips_list.append({"color": color, "value": chip_value})

        # Add the structured 'chips' list to the data dictionary
        data["chips"] = chips_list

        # Remove the raw list fields that are not part of the final model structure
        data.pop("color", None)
        data.pop("value", None)

        return data

    # NOTE: The chip validation from your original field_validator is now
    # implicitly handled by the NewChip model conversion above and the model_validator logic.

    @field_validator("name")
    def ensure_correct_name(cls, value):
        if value == "":
            raise PydanticCustomError(
                "name_error",
                f"name not correct",
            )
        return value

    @field_validator("team_id")
    def ensure_correct_team_id(cls, value):
        if value is not None and value < 0:
            raise PydanticCustomError(
                "team_id_error",
                f"Team id not correct.",
            )
        return value
