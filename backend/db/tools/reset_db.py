import sys

from backend.db.session import engine
import backend.db.base as _  # noqa, ensures all models are imported
from backend.db.base_class import Base


def drop_all():
    print(f"Dropping all tables from: {engine.url}")
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
    print("Done. All tables dropped.")


def create_all():
    print(f"Creating all tables in: {engine.url}")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
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
