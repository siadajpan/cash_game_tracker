from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship

from backend.db.base_class import Base
from backend.db.models import chip_structure
from backend.db.models.associations import user_team_association


class Team(Base):
    __tablename__ = "team"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    search_code = Column(String(200), nullable=False)

    # Owner (Many-to-One: Many teams owned by one user)
    owner_id = Column(Integer, ForeignKey("user.id"))
    owner = relationship("User", back_populates="teams_owned")

    # Players in this team (Many-to-Many)
    users = relationship(
        "User", secondary=user_team_association, back_populates="teams"
    )

    games = relationship("Game", back_populates="team")
    chip_structure = relationship("ChipStructure", back_populates="team")
