from datetime import datetime
from sqlite3 import IntegrityError
from fastapi import APIRouter, Depends, Request, Request, responses
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from pydantic_core import PydanticCustomError
from requests import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models.user import User
from backend.db.repository.chip_structure import create_new_chip_structure_db
from backend.db.session import get_db
from backend.webapps.chip_structure.chip_structure_form import (
    ChipStructureCreateForm,
)
from fastapi import status


templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/create", name="create_chip_structure_form")
async def create_chip_structure_form(
    request: Request, current_user: User = Depends(get_current_user_from_token)
):
    """
    Renders the chip structure creation form
    """

    # Prepare initial form data and context for the template
    context = {
        "request": request,
        "user_teams": current_user.teams,
        "form": {"name": datetime.today().date()},
        "errors": [],
    }

    return templates.TemplateResponse("chip_structure/create.html", context)


@router.post("/create", name="create_chip_structure")
async def create_chip_structure(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    form = await request.form()
    errors = []

    # Convert form data to a dictionary for Pydantic
    form_data_dict = {
        **form,
        "color": form.getlist("color"),  # Pass the raw lists for the model_validator
        "value": form.getlist("value"),
        "created_by": current_user.id,
    }

    try:
        chip_structure = ChipStructureCreateForm(**form_data_dict)
        create_new_chip_structure_db(chip_structure=chip_structure, db=db)
        return responses.RedirectResponse(
            url="/game/create", status_code=status.HTTP_303_SEE_OTHER
        )
    except PydanticCustomError as e:
        # Catch errors from both model_validator (which raises PydanticCustomError)
        # and standard Pydantic validation.
        errors.extend([err["msg"] for err in e.errors()])

    except ValidationError as e:
        # Catch Pydantic validation errors
        errors.extend([err["msg"] for err in e.errors()])

    except IntegrityError:
        errors.append(
            "A database error occurred (e.g., integrity constraint violation)."
        )
    except Exception as e:
        errors.append(f"An unexpected error occurred: {e}")

    return templates.TemplateResponse(
        "chip_structure/create.html",
        {
            "request": request,
            "errors": errors,
            "form": form,
            "user_teams": current_user.teams,
        },
    )
