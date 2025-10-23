from dataclasses import dataclass


@dataclass
class Day:
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


DAYS = [value for key, value in vars(Day).items() if not key.startswith("__")]

