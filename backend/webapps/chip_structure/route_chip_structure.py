from fastapi import APIRouter, Depends, Request, responses, status, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.apis.v1.route_login import get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.db.models.user import User
from backend.db.repository.chip_structure import (
    create_new_chip_structure_db,
    get_chip_structure,
    update_chip_structure_db,
    delete_chip_structure as delete_cs_db,
)
from backend.db.session import get_db
from backend.webapps.chip_structure.chip_structure_form import (
    ChipStructureCreateForm,
)
from backend.schemas.chip_structure import ChipStructureCreate

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter(include_in_schema=False)


@router.get("/manage", name="manage_chip_structures_personal")
async def manage_chip_structures(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """
    Renders a management page for all chip structures owned by the current user.
    """
    from backend.db.models.chip_structure import ChipStructure

    chip_structures = (
        db.query(ChipStructure).filter(ChipStructure.owner_id == current_user.id).all()
    )
    # Sort by name
    chip_structures = sorted(chip_structures, key=lambda x: str(x.name))

    return templates.TemplateResponse(
        "chip_structure/manage.html",
        {
            "request": request,
            "chip_structures": chip_structures,
        },
    )


@router.get("/{cs_id}/edit", name="edit_chip_structure_form")
async def edit_cs_form(
    request: Request,
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    cs = get_chip_structure(cs_id, db)
    if not cs or cs.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return templates.TemplateResponse(
        "chip_structure/edit.html",
        {"request": request, "chip_structure": cs, "form": {}},
    )


@router.post("/{cs_id}/edit", name="edit_chip_structure")
async def edit_cs(
    request: Request,
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    cs = get_chip_structure(cs_id, db)
    if not cs or cs.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    form = await request.form()
    form_data = {
        **form,
        "color": form.getlist("color"),
        "value": form.getlist("value"),
        "team_id": cs.team_id,
        "owner_id": current_user.id,
    }

    try:
        cs_form = ChipStructureCreateForm(**form_data)
        update_chip_structure_db(cs_id, cs_form, db)
        return responses.RedirectResponse(
            "/chip_structure/manage?msg=Updated successfully", 
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        return templates.TemplateResponse(
            "chip_structure/edit.html",
            {
                "request": request,
                "chip_structure": cs,
                "form": form_data,
                "errors": [str(e)],
            },
        )


@router.post("/{cs_id}/delete", name="delete_chip_structure")
async def delete_cs(
    cs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    cs = get_chip_structure(cs_id, db)
    if not cs or cs.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        delete_cs_db(cs_id, db)
        return responses.RedirectResponse(
            "/chip_structure/manage?msg=Deleted successfully",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return responses.RedirectResponse(
            f"/chip_structure/manage?error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


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
        "form": {},
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
    team_id_raw = form.get("team_id")
    team_id = int(team_id_raw) if team_id_raw and team_id_raw.isdigit() else None

    form_data_dict = {
        **form,
        "team_id": team_id,
        "color": form.getlist("color"),  # Pass the raw lists for the model_validator
        "value": form.getlist("value"),
        "owner_id": current_user.id,
    }

    try:
        chip_structure_form = ChipStructureCreateForm(**form_data_dict)
        # Map web form to DB schema
        chip_structure_schema = ChipStructureCreate(
            name=chip_structure_form.name,
            team_id=chip_structure_form.team_id,
            owner_id=current_user.id,
            chips=chip_structure_form.chips
        )
        create_new_chip_structure_db(chip_structure=chip_structure_schema, db=db)
        return responses.RedirectResponse(
            url="/game/create", status_code=status.HTTP_303_SEE_OTHER
        )
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
        },
    )
