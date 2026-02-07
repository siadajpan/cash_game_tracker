"""
Script to add missing columns to tables that are out of sync with SQLAlchemy models.
This fixes the issue where status and role columns are missing from the database.
"""
import sys
from sqlalchemy import text
from backend.db.session import engine


def add_missing_columns():
    print("Adding missing columns to database tables...")
    
    with engine.begin() as conn:
        # Create ENUM types if they don't exist
        print("Creating ENUM types if they don't exist...")
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE playerrequeststatus AS ENUM ('REQUESTED', 'APPROVED', 'DECLINED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE teamrole AS ENUM ('MEMBER', 'ADMIN');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        print("✓ ENUM types created/verified.")
        
        # Add missing columns to user_team_association
        print("Adding columns to user_team_association...")
        conn.execute(text("""
            ALTER TABLE user_team_association 
            ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';
        """))
        
        conn.execute(text("""
            ALTER TABLE user_team_association 
            ADD COLUMN IF NOT EXISTS role teamrole NOT NULL DEFAULT 'MEMBER';
        """))
        print("✓ user_team_association updated.")
        
        # Add missing status column to add_on
        print("Adding status column to add_on...")
        conn.execute(text("""
            ALTER TABLE add_on 
            ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';
        """))
        print("✓ add_on updated.")
        
        # Add missing status column to cash_out
        print("Adding status column to cash_out...")
        conn.execute(text("""
            ALTER TABLE cash_out 
            ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';
        """))
        print("✓ cash_out updated.")
        
        # Add missing status column to user_game_association
        print("Adding status column to user_game_association...")
        conn.execute(text("""
            ALTER TABLE user_game_association 
            ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';
        """))
        print("✓ user_game_association updated.")
        
        print("\n✅ Successfully added all missing columns!")
        print("\nSummary of changes:")
        print("  - user_team_association: added 'status' and 'role' columns")
        print("  - add_on: added 'status' column")
        print("  - cash_out: added 'status' column")
        print("  - user_game_association: added 'status' column")


if __name__ == "__main__":
    try:
        add_missing_columns()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

