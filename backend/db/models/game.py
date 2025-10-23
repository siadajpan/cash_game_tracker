from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class Game(Base):
    id = Column(Integer, primary_key=True, index=True)
    user = relationship("Player", back_populates="game")
    date = Column(String, nullable=False)
    buy_ins = relationship(argument="BuyIn", back_populates="game")
    add_ons = relationship(argument="AddOn", back_populates="game")
