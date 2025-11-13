
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.player_request_status import PlayerRequestStatus



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
