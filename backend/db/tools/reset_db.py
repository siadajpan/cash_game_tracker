import sys
from sqlalchemy import text

from backend.db.session import engine
import backend.db.base as _  # noqa, ensures all models are imported
from backend.db.base_class import Base
from backend.db.models.player_request_status import PlayerRequestStatusEnum
from backend.db.models.team_role import TeamRoleEnum


def drop_all():
    """Drop all tables and ENUM types using CASCADE to handle circular dependencies."""
    print(f"Dropping all tables from: {engine.url}")
    with engine.begin() as conn:
        # Use CASCADE to handle circular foreign key dependencies
        # This is necessary because chip_structure and team have circular FKs
        print("Dropping all tables with CASCADE...")
        try:
            # Get all table names
            from sqlalchemy import inspect
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            
            if tables:
                # Drop each table with CASCADE
                for table in tables:
                    try:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
                    except Exception as e:
                        print(f"Warning: Could not drop table {table}: {e}")
                print(f"✓ Dropped {len(tables)} tables.")
            else:
                print("No tables to drop.")
        except Exception as e:
            print(f"Warning during table drop: {e}")
            # Fallback: try Base.metadata.drop_all anyway
            try:
                Base.metadata.drop_all(bind=conn)
            except Exception as e2:
                print(f"Could not use metadata.drop_all: {e2}")
        
        # Drop ENUM types (they persist even after tables are dropped)
        print("Dropping ENUM types...")
        try:
            conn.execute(text("DROP TYPE IF EXISTS playerrequeststatus CASCADE;"))
            conn.execute(text("DROP TYPE IF EXISTS teamrole CASCADE;"))
            print("✓ ENUM types dropped.")
        except Exception as e:
            print(f"Warning: Could not drop ENUM types: {e}")
    
    print("✓ Done. Database cleaned.")


def create_all():
    """Create ENUM types and all tables."""
    print(f"Creating all tables in: {engine.url}")
    with engine.begin() as conn:
        # Create ENUM types first
        print("Creating ENUM types...")
        try:
            PlayerRequestStatusEnum.create(bind=conn, checkfirst=True)
            TeamRoleEnum.create(bind=conn, checkfirst=True)
            print("✓ ENUM types created.")
        except Exception as e:
            print(f"Note: {e}")
            print("Continuing with table creation...")
        
        # Then create tables
        print("Creating tables...")
        Base.metadata.create_all(bind=conn)
        print("✓ Tables created.")
    
    print("✓ Done. All tables created successfully.")


def reset_all():
    """Drop and recreate all tables and ENUM types."""
    print("\n" + "="*60)
    print("DATABASE RESET - This will DELETE ALL DATA!")
    print("="*60 + "\n")
    drop_all()
    print()
    create_all()
    print("\n" + "="*60)
    print("✅ Database has been reset successfully!")
    print("="*60 + "\n")


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: reset_db.py [drop|create|reset]")
        print()
        print("Commands:")
        print("  drop   - Drop all tables and ENUM types")
        print("  create - Create ENUM types and all tables")
        print("  reset  - Drop everything and recreate (DELETES ALL DATA)")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    
    try:
        if cmd == "drop":
            drop_all()
        elif cmd == "create":
            create_all()
        elif cmd == "reset":
            reset_all()
        else:
            print(f"Unknown command: '{cmd}'")
            print("Use 'drop', 'create', or 'reset'")
            sys.exit(2)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

