from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.responses import Response

from backend.apis.utils import OAuth2PasswordBearerWithCookie
from backend.core.config import settings
from backend.core.hashing import Hasher
from backend.core.security import create_access_token
from backend.db.session import get_db
from backend.schemas.tokens import Token
from backend.db.repository.user import get_user_by_email

router = APIRouter()


def authenticate_user(email: str, password: str, db: Session):
    user = get_user_by_email(email=email, db=db)
    if not user or not Hasher.verify_password(password, user.hashed_password):
        return None
    return user


@router.post("/token", response_model=Token)
def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect username or password {form_data.username}",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response.set_cookie(
        key="access_token", value=f"Bearer {access_token}", httponly=True
    )
    return {"access_token": access_token, "token_type": "bearer"}


oauth2_scheme = OAuth2PasswordBearerWithCookie(
    tokenUrl="/login/token", auto_error=False
)


def get_current_user_from_token(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    if not token:
        # No token provided (unauthenticated user)
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(
            token, key=settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(email=email, db=db)
    if user is None:
        raise credentials_exception
    return user


def optional_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        return get_current_user_from_token(token, db)
    except JWTError:
        return None
    except HTTPException:
        return None
def get_current_user(request, db):
    token = request.cookies.get("access_token")
    if token is None:
        return None
    scheme, param = get_authorization_scheme_param(
        token
    )  # scheme will hold "Bearer" and param will hold actual token value
    current_user = get_current_user_from_token(token=param, db=db)
    return current_user
