from sqlalchemy import Column, ForeignKey, Integer, Float, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models import chip_structure


class Chip(Base):
    id = Column(Integer, primary_key=True, index=True)
    color = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    chip_structure_id = Column(Integer, ForeignKey("chip_structure.id"))

    chip_structure = relationship("ChipStructure", back_populates="chips")
