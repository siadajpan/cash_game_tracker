from pydantic import BaseModel, EmailStr

from backend.db.models.doctors import DoctorSpeciality


class DoctorCreate(BaseModel):
    email: EmailStr
    password: str
    speciality: DoctorSpeciality
    first_name: str
    last_name: str


class ShowDoctor(BaseModel):
    id: str
    user_id: str
    email: str
    first_name: str
    last_name: str
    speciality: DoctorSpeciality

    class Config:
        orm_mode = True
