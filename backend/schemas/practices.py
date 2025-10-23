from pydantic import BaseModel


class PracticeCreate(BaseModel):
    email: str
    password: str
    name: str
    postcode: str
    city: str
    address: str


class PracticeShow(BaseModel):
    id: str
    user_id: str
    name: str
    postcode: str
    city: str
    address: str

    class Config:
        orm_mode = True
