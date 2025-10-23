from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class WorkingHours(Base):
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor.id"))
    doctor = relationship("Doctor", back_populates="working_hours")
    practice_id = Column(Integer, ForeignKey("practice.id"))
    practice = relationship("Practice", back_populates="working_hours")
    day_of_week = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
