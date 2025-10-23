from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class Practice(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="practice")
    name = Column(String, nullable=False)
    postcode = Column(String, nullable=False)
    city = Column(String, nullable=False)
    address = Column(String, nullable=False)
    working_hours = relationship("WorkingHours", back_populates="practice")
    phone_number = Column(String, nullable=False)
    descriptor = Column(String, unique=True, nullable=False)
