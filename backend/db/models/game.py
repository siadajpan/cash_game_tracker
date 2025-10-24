from ecdsa.curves import Curve
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.associations import user_game_association


class Game(Base):
    __tablename__ = 'game'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False) # Consider using Date or DateTime type instead of String
    default_buy_in = Column(Float, nullable=False)
    running = Column(Boolean, nullable=False)

    # Owner (Many-to-One: Many games owned by one user)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="games_owned")

    team_id = Column(Integer, ForeignKey("team.id"))
    team = relationship("Team",  back_populates="games")

    # Players in this game (Many-to-Many)
    players = relationship(
        "User",
        secondary=user_game_association,
        back_populates="games_played"
    )
