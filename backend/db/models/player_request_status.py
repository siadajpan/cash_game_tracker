from sqlalchemy import Column, Integer
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


# Define Python enum
class PlayerRequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


# Map to PostgreSQL ENUM
PlayerRequestStatusEnum = ENUM(
    PlayerRequestStatus,
    name="playerrequeststatus",
    create_type=False,  # don't create automatically
)


# Example table using the enum
class PlayerRequest(Base):
    __tablename__ = "player_requests"
    id = Column(Integer, primary_key=True)
    status = Column(PlayerRequestStatusEnum, nullable=False)
