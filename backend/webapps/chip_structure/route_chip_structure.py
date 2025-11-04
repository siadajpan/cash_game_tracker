
import datetime
from fastapi import APIRouter, Depends, Request, Request, responses
from fastapi.templating import Jinja2Templates
from requests import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models.user import User
from backend.db.repository.chip_structure import add_team_chip_structure, create_new_chip_structure_db
from backend.db.repository.team import get_team_by_id
from backend.db.session import get_db
from backend.schemas.games import GameCreate
from backend.webapps.chip_structure.chip_structure_form import ChipStructureCreateForm


templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/create", name="create_chip_structure_form")
async def create_chip_structure_form(
    request: Request, current_user: User = Depends(get_current_user_from_token), game_id: int = None
):
    """
    Renders the chip structure creation form
    """

    # Prepare initial form data and context for the template
    context = {
        "request": request,
        "errors": [],
    }

    return templates.TemplateResponse("chip_structure/create.html", context)


@router.post("/create/{team_id}", name="create_chip_structure")
async def create_chip_structure(
    request: Request,
    team_id: int,
    game_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    form = ChipStructureCreateForm(request)
    await form.load_data()

    template_name = "game/create.html"
    errors = []

    # 1. Validation checks (from form.is_valid and additional checks)
    if not await form.is_valid():
        errors.extend(form.errors)

    # Check if the team exists (Critical step for foreign key integrity)
    team = get_team_by_id(team_id, db)
    if not team:
        errors.append("Selected team does not exist.")

    if not errors:
        try:
            # Use all extracted variables
            date = str(
                datetime.today().date()
            )  # Using today's date as a fallback, but form.date is better

            # CRITICAL: Pass the team_id to the GameCreate Pydantic model
            new_chip_structure_data = ChipStructureCreateForm(
                name=form.name,
                team_id=team_id,
                blinds=form.blinds,
                ante=form.ante,
                created_by=current_user.id
            )
            chip_structure = create_new_chip_structure_db(
                chip_structure=new_chip_structure_data, current_user=current_user, db=db
            )
            add_team_chip_structure(team_id=team_id,
                                    chip_structure_id=chip_structure.id,
                                    db=db)  

            return responses.RedirectResponse(
                f"/game/{game.id}?msg=Game created successfully",
                status_code=status.HTTP_302_FOUND,
            )
        
        except IntegrityError:
            errors.append(
                "A database error occurred (e.g., integrity constraint violation)."
            )
        except Exception as e:
            errors.append(f"An unexpected error occurred: {e}")

    # Re-render with all submitted data
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "errors": errors,
            # CRITICAL FIX: Package submitted data into a 'form' object for the template
            "form": {
                "default_buy_in": default_buy_in,
                "team_id": team_id,
                # Add any other fields if you add them to the form/template
            },
            # You must also pass user_teams back for the dropdown to work
            "user_teams": current_user.teams,
        },
    )
from typing import List, Optional, Type