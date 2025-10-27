from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from backend.db.base_class import Base


user_team_association = Table(
    "user_team_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("team.id"), primary_key=True),
)

# Association table for User-Game many-to-many (Players in a Game)
user_game_association = Table(
    "user_game_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("game_id", Integer, ForeignKey("game.id"), primary_key=True),
)
