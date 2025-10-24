from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.associations import user_game_association


class Game(Base):
    __tablename__ = 'game'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False) # Consider using Date or DateTime type instead of String

    # Owner (Many-to-One: Many games owned by one user)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="games_owned")

    # Players in this game (Many-to-Many)
    players = relationship(
        "User",
        secondary=user_game_association,
        back_populates="games_played"
    )
