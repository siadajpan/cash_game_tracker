from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models.speciality import DoctorSpeciality


class Doctor(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="doctor")
    speciality = Column(Enum(DoctorSpeciality), nullable=False)
    first_name = Column(String(200), nullable=False)
    last_name = Column(String(200), nullable=False)
    working_hours = relationship("WorkingHours", back_populates="doctor")
