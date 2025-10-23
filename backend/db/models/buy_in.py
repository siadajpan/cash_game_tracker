from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class BuyIn(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="buy_ins")
    game_id = Column(Integer, ForeignKey("game.id"))
    game = relationship("Game", back_populates="buy_ins")
    time = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
