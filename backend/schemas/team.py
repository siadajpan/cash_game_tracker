from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str
    search_code: str


class TeamShow(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True
