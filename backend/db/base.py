from backend.db.base_class import Base  # noqa

# Import all models here
from backend.db.models.user import User  # noqa
from backend.db.models.cash_out import CashOut  # noqa
from backend.db.models.team import Team  # noqa
from backend.db.models.game import Game  # noqa
from backend.db.models.chip_structure import ChipStructure  # noqa
from backend.db.models.chip import Chip  # noqa
from backend.db.models.buy_in import BuyIn  # noqa
from backend.db.models.chip_amount import ChipAmount  # noqa
from backend.db.models.add_on import AddOn  # noqa

# Import association tables
from backend.db.models.associations import user_team_association  # noqa
from backend.db.models.associations import user_game_association  # noqa

# List of all models for metadata
# models = (User, Team, Game, ChipStructure, Chip, BuyIn, CashOut, AddOn, ChipAmount)
