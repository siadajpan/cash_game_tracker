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
    Nuclear option: Drop and recreate the entire public schema.
    This handles ANY circular dependencies or complex FK relationships.
    """
    print("\n" + "="*60)
    print("NUCLEAR DATABASE RESET")
    print("This will DROP THE ENTIRE PUBLIC SCHEMA and recreate it")
    print("="*60 + "\n")
    
    with engine.begin() as conn:
        print("Dropping public schema CASCADE...")
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        print("✓ Public schema dropped.")
        
        print("Creating public schema...")
        conn.execute(text("CREATE SCHEMA public;"))
        print("✓ Public schema created.")
        
        print("Granting permissions...")
        # Grant permissions to the database user
        db_user = engine.url.username
        conn.execute(text(f"GRANT ALL ON SCHEMA public TO {db_user};"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        print("✓ Permissions granted.")
    
    print("\nCreating ENUM types and tables...")
    with engine.begin() as conn:
        # Create ENUM types
        print("Creating ENUM types...")
        PlayerRequestStatusEnum.create(bind=conn, checkfirst=True)
        TeamRoleEnum.create(bind=conn, checkfirst=True)
        print("✓ ENUM types created.")
        
        # Create all tables
        print("Creating tables...")
        Base.metadata.create_all(bind=conn)
        print("✓ Tables created.")
    
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
