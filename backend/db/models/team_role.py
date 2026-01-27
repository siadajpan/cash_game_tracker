import enum
from sqlalchemy.dialects.postgresql import ENUM

class TeamRole(str, enum.Enum):
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"

TeamRoleEnum = ENUM(
    TeamRole,
    name="teamrole",
    create_type=False,
)
