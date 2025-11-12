from sqlalchemy import Column, ForeignKey, Integer, Float, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models import chip_structure


class ChipAmount(Base):
    __tablename__ = "chip_amount"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    chip_id = Column(Integer, ForeignKey("chip.id"))
    cash_out_id = Column(Integer, ForeignKey("cash_out.id"))

    cash_out = relationship("CashOut", back_populates="chip_amounts")
    chip = relationship("Chip")
