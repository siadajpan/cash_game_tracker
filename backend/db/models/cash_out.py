from sqlalchemy import Column, ForeignKey, Integer, String, Float, Enum
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.add_on import PlayerRequestStatus


class CashOut(Base):
    __tablename__ = "cash_out"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    game_id = Column(Integer, ForeignKey("game.id"))
    time = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(
        Enum(PlayerRequestStatus), default=PlayerRequestStatus.REQUESTED, nullable=False
    )
    
    chip_amounts = relationship("ChipAmount", back_populates="cash_out", cascade="all, delete-orphan")
    user = relationship("User", back_populates="cash_outs")
    game = relationship("Game", back_populates="cash_outs")
