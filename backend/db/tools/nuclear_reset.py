"""
Alternative reset script using schema drop.
This is the nuclear option - drops the entire public schema and recreates it.
Use this if reset_db.py has issues with circular dependencies.
"""
import sys
from sqlalchemy import text

from backend.db.session import engine
import backend.db.base as _  # noqa, ensures all models are imported
from backend.db.base_class import Base
from backend.db.models.player_request_status import PlayerRequestStatusEnum
from backend.db.models.team_role import TeamRoleEnum


def nuclear_reset():
    """
    Nuclear option: Drop all database objects and recreate them.
    This handles ANY circular dependencies or complex FK relationships.
    """
    print("\n" + "="*60)
    print("NUCLEAR DATABASE RESET")
    print("This will DROP ALL TABLES, TYPES, and SEQUENCES")
    print("="*60 + "\n")
    
    with engine.begin() as conn:
        # Drop all tables with CASCADE
        print("Dropping all tables with CASCADE...")
        try:
            from sqlalchemy import inspect
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            
            if tables:
                for table in tables:
                    try:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
                        print(f"  ✓ Dropped table: {table}")
                    except Exception as e:
                        print(f"  Warning: Could not drop table {table}: {e}")
                print(f"✓ Dropped {len(tables)} tables.")
            else:
                print("No tables found.")
        except Exception as e:
            print(f"Warning during table drop: {e}")
        
        # Drop all types (ENUMs)
        print("\nDropping all custom types...")
        try:
            conn.execute(text("DROP TYPE IF EXISTS playerrequeststatus CASCADE;"))
            conn.execute(text("DROP TYPE IF EXISTS teamrole CASCADE;"))
            print("✓ Custom types dropped.")
        except Exception as e:
            print(f"Warning: Could not drop types: {e}")
        
        # Drop all sequences
        print("\nDropping all sequences...")
        try:
            result = conn.execute(text("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public';
            """))
            sequences = [row[0] for row in result]
            
            if sequences:
                for seq in sequences:
                    try:
                        conn.execute(text(f'DROP SEQUENCE IF EXISTS "{seq}" CASCADE;'))
                        print(f"  ✓ Dropped sequence: {seq}")
                    except Exception as e:
                        print(f"  Warning: Could not drop sequence {seq}: {e}")
                print(f"✓ Dropped {len(sequences)} sequences.")
            else:
                print("No sequences found.")
        except Exception as e:
            print(f"Warning during sequence drop: {e}")
    
    print("\n" + "="*60)
    print("Creating ENUM types and tables...")
    print("="*60 + "\n")
    
    with engine.begin() as conn:
        # Create ENUM types
        print("Creating ENUM types...")
        PlayerRequestStatusEnum.create(bind=conn, checkfirst=True)
        TeamRoleEnum.create(bind=conn, checkfirst=True)
        print("✓ ENUM types created.")
        
        # Create all tables
        print("\nCreating tables...")
        Base.metadata.create_all(bind=conn)
        print("✓ All tables created.")
    
    print("\n" + "="*60)
    print("✅ NUCLEAR RESET COMPLETE!")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        nuclear_reset()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
