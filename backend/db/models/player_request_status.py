import enum

# Define the status enum
class PlayerRequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
