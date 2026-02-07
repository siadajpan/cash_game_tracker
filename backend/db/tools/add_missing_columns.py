"""
Script to add missing columns to user_team_association table.
This fixes the issue where status and role columns are missing from the database.
"""
import sys
from sqlalchemy import text
from backend.db.session import engine


def add_missing_columns():
    print("Adding missing columns to user_team_association table...")
    
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
        
        print("ENUM types created/verified.")
        
        # Add the status column
        print("Adding status column...")
        conn.execute(text("""
            ALTER TABLE user_team_association 
            ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';
        """))
        
        # Add the role column
        print("Adding role column...")
        conn.execute(text("""
            ALTER TABLE user_team_association 
            ADD COLUMN IF NOT EXISTS role teamrole NOT NULL DEFAULT 'MEMBER';
        """))
        
        print("✓ Successfully added missing columns!")


if __name__ == "__main__":
    try:
        add_missing_columns()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
