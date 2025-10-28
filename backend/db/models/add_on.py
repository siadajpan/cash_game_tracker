import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


# Define the status enum
class PlayerRequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class AddOn(Base):
    __tablename__ = "add_on"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    game_id = Column(Integer, ForeignKey("game.id"))
    time = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(
        Enum(PlayerRequestStatus), default=PlayerRequestStatus.REQUESTED, nullable=False
    )

    user = relationship("User", back_populates="add_ons")
    game = relationship("Game", back_populates="add_ons")
