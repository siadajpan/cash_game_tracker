from sqlalchemy import Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class AddOn(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="add_ons")
    game_id = Column(Integer, ForeignKey("game.id"))
    game = relationship("Game", back_populates="add_ons")
    time = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
