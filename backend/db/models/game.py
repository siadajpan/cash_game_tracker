from ecdsa.curves import Curve
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.chip_structure import ChipStructure  # direct import for clarity


class Game(Base):
    __tablename__ = "game"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(
        String, nullable=False
    )  # Consider using Date or DateTime type instead of String
    default_buy_in = Column(Float, nullable=False)
    running = Column(Boolean, nullable=False)

    # Owner (Many-to-One: Many games owned by one user)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="games_owned")

    team_id = Column(Integer, ForeignKey("team.id"))
    team = relationship("Team", back_populates="games")

    chip_structure_id = Column(Integer, ForeignKey("chip_structure.id"))
    chip_structure = relationship("ChipStructure", back_populates="games")

    # Players in this team (Many-to-Many)
    user_associations = relationship(
        "UserGame",
        back_populates="game",
        cascade="all, delete-orphan",  # Recommended for Association Objects
    )
    buy_ins = relationship("BuyIn", back_populates="game", cascade="all, delete-orphan")
    add_ons = relationship("AddOn", back_populates="game", cascade="all, delete-orphan")
    cash_outs = relationship(
        "CashOut", back_populates="game", cascade="all, delete-orphan"
    )

    @property
    def players(self):
        # Retrieve the User objects via the association objects
        return [assoc.user for assoc in self.user_associations]
