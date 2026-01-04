from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), nullable=False, unique=True)
    hashed_password = Column(String(200), nullable=False)
    is_superuser = Column(Boolean(), default=False)
    is_active = Column(Boolean(), default=False)
    nick = Column(String(200), nullable=False)

    teams_owned = relationship("Team", back_populates="owner")

    # Teams a user belongs to (Many-to-Many)
    team_associations = relationship(
        "UserTeam",
        back_populates="user",
        cascade="all, delete-orphan",  # Recommended for Association Objects
    )

    # Teams a user belongs to (Many-to-Many)
    game_associations = relationship(
        "UserGame",
        back_populates="user",
        cascade="all, delete-orphan",  # Recommended for Association Objects
    )

    # Games a user owns (One-to-Many: One user owns many games)
    games_owned = relationship("Game", back_populates="owner")

    # NEW: Buy-ins and Add-ons
    buy_ins = relationship("BuyIn", back_populates="user", cascade="all, delete-orphan")
    add_ons = relationship("AddOn", back_populates="user", cascade="all, delete-orphan")
    cash_outs = relationship(
        "CashOut", back_populates="user", cascade="all, delete-orphan"
    )

    verification = relationship(
        "UserVerification", back_populates="user", uselist=False
    )

    @property
    def teams(self):
        # Retrieve the Team objects via the association objects
        return [assoc.team for assoc in self.team_associations]

    @property
    def games_played(self):
        # Retrieve the Team objects via the association objects
        return [assoc.game for assoc in self.game_associations]
