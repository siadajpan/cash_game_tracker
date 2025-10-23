from typing import List

from fastapi import APIRouter, Depends, Request, responses, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from backend.db.repository.practices import create_new_practice, retrieve_practice, list_practices
from backend.db.session import get_db
from backend.schemas.practices import PracticeCreate, PracticeShow
from backend.webapps.practices.forms import PracticeCreateForm
from db.repository.doctors import retrieve_practice_doctors_and_working_hours

templates = Jinja2Templates(directory="templates")
router = APIRouter(include_in_schema=False)


@router.post("/create", response_model=PracticeShow)
def create_practice(practice: PracticeCreate, db: Session = Depends(get_db)):
    new_practice = create_new_practice(practice, db)
    return new_practice


@router.get("/get/{practice_id}")
def read_practice(practice_id: int, db: Session = Depends(get_db)):
    practice = retrieve_practice(practice_id=practice_id, db=db)
    if not practice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Practice with that id {id} doesn't exist",
        )
    return practice


@router.get("/all", response_model=List[PracticeShow])
def read_practices(db: Session = Depends(get_db)):
    practices = list_practices(db=db)

    return practices


@router.get("/details/{practice_id}")
async def practice_details(
        practice_id, request: Request, db: Session = Depends(get_db)
):
    # retrieve all doctors working here
    practice_doctors = retrieve_practice_doctors_and_working_hours(practice_id=practice_id, db=db)
    print("practice_doctors", practice_doctors)
    practice = retrieve_practice(practice_id, db)
    return templates.TemplateResponse(
        "practices/details.html",
        {
            "request": request,
            "practice": practice,
            "doctors_working_hours": practice_doctors,
        },
    )


@router.get("/register/")
def register_form(request: Request):
    return templates.TemplateResponse("practices/register.html", {"request": request})


@router.post("/register/")
async def register(request: Request, db: Session = Depends(get_db)):
    form = PracticeCreateForm(request)
    await form.load_data()
    if await form.is_valid():
        new_practice = PracticeCreate(
            name=form.name,
            email=form.email,
            password=form.password,
            address=form.address,
            postcode=form.postcode,
            city=form.city,
        )
        try:
            create_new_practice(practice=new_practice, db=db)
            return responses.RedirectResponse(
                "/?msg=Successfully registered", status_code=status.HTTP_302_FOUND
            )  # default is post request, to use get request added status code 302
        except IntegrityError:
            form.errors.append("User with that e-mail already exists.")
            return templates.TemplateResponse("practices/register.html", form.__dict__)
    return templates.TemplateResponse("practices/register.html", form.__dict__)
