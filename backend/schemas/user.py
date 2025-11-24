from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nick: str


class UserShow(BaseModel):
    id: int
    email: str
    nick: str

    class Config:
        from_attributes = True
