from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    hashed_password = Column(String, nullable=False)
    is_superuser = Column(Boolean(), default=False)
    doctor = relationship("Doctor", back_populates="user")
    practice = relationship("Practice", back_populates="user")
