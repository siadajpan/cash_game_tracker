from sqlalchemy import Column, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class ChipStructure(Base):
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("team.id"))
    game_id = Column(Integer, ForeignKey("game.id"))

    team = relationship("Team", back_populates="chip_structures")
    game = relationship("Game", back_populates="chip_structures")
    chip = relationship("Chip", back_populates="chip_structure")
