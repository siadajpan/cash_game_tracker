from sqlalchemy import Column, ForeignKey, Integer, Float, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class ChipStructure(Base):
    __tablename__ = "chip_structure"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    team_id = Column(Integer, ForeignKey("team.id"))

    team = relationship("Team", back_populates="chip_structure")
    games = relationship("Game", back_populates="chip_structure")
    chips = relationship("Chip", back_populates="chip_structure")