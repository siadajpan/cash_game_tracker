
from datetime import datetime
from sqlite3 import IntegrityError
from fastapi import APIRouter, Depends, Request, Request, responses
from fastapi.templating import Jinja2Templates
from requests import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models import chip
from backend.db.models.user import User
from backend.db.repository.chip_structure import create_new_chip_structure_db
from backend.db.repository.team import get_team_by_id
from backend.db.session import get_db
from backend.schemas.chip_structure import ChipStructureCreate
from backend.schemas.chips import ChipCreate
from backend.schemas.games import GameCreate
from backend.webapps.chip_structure.chip_structure_form import ChipStructureCreateForm
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

        "errors": [],
    }

    return templates.TemplateResponse("chip_structure/create.html", context)


@router.post("/create", name="create_chip_structure")
async def create_chip_structure(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    form = ChipStructureCreateForm(request)
    await form.load_data()
    print("Form chips:", form.chips)
    errors = []

    # Validate form
    if not await form.is_valid():
        errors.extend(form.errors)

    # Check team validity
    team = get_team_by_id(form.team_id, db)
    if not team:
        errors.append("Selected team does not exist.")

    if not form.chips or len(form.chips) == 0:
        errors.append("At least one chip value must be provided.")

    # If errors, return immediately
    if errors:
        return templates.TemplateResponse(
            "chip_structure/create.html",
            {
                "request": request,
                "errors": errors,
                "form": {"team_id": form.team_id, "chips": form.chips},
                "user_teams": current_user.teams,
            },
        )

    try:
        # Create a new ChipStructure
        new_chip_structure_data = ChipStructureCreate(
            team_id=form.team_id, chips=form.chips
        )
        create_new_chip_structure_db(
            chip_structure=new_chip_structure_data, db=db
        )
        print("returning redirect")
        return responses.RedirectResponse(url="/game/create", status_code=status.HTTP_303_SEE_OTHER)

    except IntegrityError:
        errors.append("A database error occurred (e.g., integrity constraint violation).")
    except Exception as e:
        errors.append(f"An unexpected error occurred: {e}")
        print(e)

    return templates.TemplateResponse(
        "chip_structure/create.html",
        {
            "request": request,
            "errors": errors,
            "form": {"team_id": form.team_id, "chips": form.chips},
            "user_teams": current_user.teams,
        },
    )