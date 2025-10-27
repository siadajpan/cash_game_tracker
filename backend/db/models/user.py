from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.associations import user_team_association, user_game_association


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    is_superuser = Column(Boolean(), default=False)
    nick = Column(String(200), nullable=False)

    teams_owned = relationship("Team", back_populates="owner")
    # Teams a user belongs to (Many-to-Many)
    teams = relationship(
        "Team", secondary=user_team_association, back_populates="users"
    )

    # Games a user has played in (Many-to-Many)
    games_played = relationship(  # Renamed 'games' to 'games_played' for clarity
        "Game", secondary=user_game_association, back_populates="players"
    )

    # Games a user owns (One-to-Many: One user owns many games)
    games_owned = relationship(
        "Game", back_populates="owner"
    )  # Renamed back_populates to 'owner'

    # NEW: Buy-ins and Add-ons
    buy_ins = relationship("BuyIn", back_populates="user", cascade="all, delete-orphan")
    add_ons = relationship("AddOn", back_populates="user", cascade="all, delete-orphan")
