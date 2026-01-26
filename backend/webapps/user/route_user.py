from typing import List
from fastapi import APIRouter, Depends, Request, responses, status
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from backend.db.session import get_db
from backend.db.models.user import User
from backend.schemas.user import UserShow
from backend.apis.v1.route_login import get_current_user_from_token
from backend.core.config import TEMPLATES_DIR
from backend.webapps.user.forms import UserProfileForm
from backend.db.repository.user import get_user_by_email, update_user_password
from backend.core.hashing import Hasher

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/list", response_model=List[UserShow])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


@router.get("/profile")
async def profile_view(
    request: Request,
    user: User = Depends(get_current_user_from_token)
):
    # Pass empty form so template can access defaults from user object
    return templates.TemplateResponse(
        "user/profile.html", {"request": request, "user": user, "form": {}}
    )


@router.post("/profile")
async def profile_update(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_token)
):
    form = UserProfileForm(request)
    await form.load_data()
    
    if await form.is_valid():
        # Check email uniqueness if changed
        if form.email != user.email:
            existing_user = get_user_by_email(form.email, db)
            if existing_user and existing_user.id != user.id:
                form.errors.append("Email already registered.")
                
        if not form.errors:
            # Update fields
            user.nick = form.nick
            user.email = form.email
            
            if form.password:
                user.hashed_password = Hasher.get_password_hash(form.password)
                
            try:
                db.add(user)
                db.commit()
                db.refresh(user)
                return templates.TemplateResponse(
                    "user/profile.html", 
                    {
                        "request": request, 
                        "user": user, 
                        "form": form,
                        "msg": "Profile updated successfully"
                    }
                )
            except Exception as e:
                form.errors.append(f"An error occurred: {e}")

    return templates.TemplateResponse(
        "user/profile.html", 
        {"request": request, "user": user, "form": form, "errors": form.errors}
    )
