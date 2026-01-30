from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class Team(Base):
    __tablename__ = "team"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    search_code = Column(String(200), nullable=False)

    # Players in this team (Many-to-Many)
    user_associations = relationship(
        "UserTeam",
        back_populates="team",
        cascade="all, delete-orphan",  # Recommended for Association Objects
    )

    games = relationship("Game", back_populates="team", cascade="all, delete-orphan")
    chip_structure = relationship("ChipStructure", back_populates="team")

    @property
    def users(self):
        # Retrieve the User objects via the association objects
        return [assoc.user for assoc in self.user_associations if assoc.user]
