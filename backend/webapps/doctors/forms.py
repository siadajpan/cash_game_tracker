import dataclasses
from typing import List, Optional, Type

from fastapi import Request
from starlette.datastructures import FormData

from backend.db.models.doctors import DoctorSpeciality
from schemas.working_hours import WorkingHoursCreate
from webapps.utils import types


class DoctorCreateForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.first_name: Optional[str] = None
        self.last_name: Optional[str] = None
        self.speciality: Optional[DoctorSpeciality] = None
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.repeat_password: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.first_name = form.get("first_name")
        self.last_name = form.get("last_name")
        self.email = form.get("email")
        self.speciality = form.get("speciality")
        self.password = form.get("password")
        self.repeat_password = form.get("repeat_password")

    async def is_valid(self):
        if not self.first_name:
            self.errors.append("First name is required")
        if not self.last_name:
            self.errors.append("Last name is required")
        if not self.password or len(self.password) < 4:
            self.errors.append("Password needs to be at least 4 characters")
        if not self.email:
            self.errors.append("Wrong email address")
        if self.password != self.repeat_password:
            self.errors.append("Passwords don't match")
        return len(self.errors) == 0


class DayWorkingHours:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __str__(self):
        return f"{self.start} - {self.end}"


class WorkingHoursCreateForm:
    def __init__(self, request: Request):
        self.request = request
        self.working_hours: Optional[List[WorkingHoursCreate]] = []

    def get_working_data_day(self, form: FormData, day: str):
        start = form.get(f"{day}_start")
        end = form.get(f"{day}_end")
        if start and end:
            return {
                "day_of_week": day,
                "start_time": start,
                "end_time": end,
            }

        return None

    async def load_data(self, practice_id):
        form = await self.request.form()

        for day in types.DAYS:
            working_hours = self.get_working_data_day(form, day)
            if working_hours:
                working_hours["practice_id"] = practice_id
                working_hours_create = WorkingHoursCreate(**working_hours)
                self.working_hours.append(working_hours_create)

    async def is_valid(self):
        return True
