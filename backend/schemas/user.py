from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nick: str


class UserShow(BaseModel):
    id: str
    email: str
    nick: str

    class Config:
        from_attributes = True
