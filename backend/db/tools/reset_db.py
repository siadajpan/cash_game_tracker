"""Utility to drop and recreate all database tables.

Usage:
  poetry run python backend/tools/reset_db.py drop   # drop all tables
  poetry run python backend/tools/reset_db.py create # create all tables
  poetry run python backend/tools/reset_db.py reset  # drop then create

This script uses the project's SQLALCHEMY_DATABASE_URL from
`backend.core.config.settings` via `backend.db.session.engine` and the
declarative `Base` in `backend.db.base_class` to operate on metadata.

WARNING: Dropping all tables is destructive. Make sure you have backups
or you understand the data loss implications before running `drop` or
`reset`.
"""
import sys

from backend.db.base_class import Base
from backend.db.session import engine


def drop_all():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Done. All tables dropped.")


def create_all():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. All tables created.")


def main():
    if len(sys.argv) < 2:
        print("Usage: reset_db.py [drop|create|reset]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "drop":
        drop_all()
    elif cmd == "create":
        create_all()
    elif cmd == "reset":
        drop_all()
        create_all()
    else:
        print("Unknown command. Use drop, create or reset.")
        sys.exit(2)


if __name__ == "__main__":
    drop_all()
    # create_all()
    # main()
