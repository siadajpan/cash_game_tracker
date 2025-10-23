from datetime import datetime

from pydantic import BaseModel, validator

from backend.schemas.types import DayOfWeek


class WorkingHoursCreate(BaseModel):
    day_of_week: str
    start_time: str
    end_time: str
    practice_id: str

    @validator("day_of_week")
    def ensure_correct_day(cls, value):
        if value not in (day for (i, day) in DayOfWeek):
            raise ValueError("Wrong day of week")
        return value

    @validator("start_time", "end_time")
    def ensure_correct_time(cls, value):
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError:
            raise ValueError("Wrong time format")
        return value

    @staticmethod
    def validate_start_less_than_end(start_time, end_time):
        if datetime.strptime(start_time, "%H:%M") >= datetime.strptime(
            end_time, "%H:%M"
        ):
            raise ValueError("Start time is after end time")


class WorkingHoursShow(BaseModel):
    day_of_week: str
    start_time: str
    end_time: str

    class Config:
        orm_mode = True
