from sqlalchemy import Column, ForeignKey, Integer, Enum
from sqlalchemy.orm import relationship

# Assuming Base and the status definitions are available
from backend.db.base_class import Base

from backend.db.models.player_request_status import (
    PlayerRequestStatus,
    PlayerRequestStatusEnum,
)


class UserGame(Base):
    __tablename__ = "user_game_association"

    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    game_id = Column(Integer, ForeignKey("game.id"), primary_key=True)

    status = Column(
        PlayerRequestStatusEnum, default=PlayerRequestStatus.REQUESTED, nullable=False
    )
    user = relationship("User", back_populates="game_associations")
    game = relationship("Game", back_populates="user_associations")
