from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str


class TeamShow(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True
