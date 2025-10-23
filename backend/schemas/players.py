from pydantic import BaseModel, EmailStr

from backend.db.models.users import DoctorSpeciality


class PlayerCreate(BaseModel):
    email: EmailStr
    password: str
    nick: str


class PlayerShow(BaseModel):
    id: str
    email: str
    nick: str

    class Config:
        orm_mode = True
