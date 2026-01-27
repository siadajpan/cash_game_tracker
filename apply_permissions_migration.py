from sqlalchemy import create_engine, text
from backend.core.config import settings
import sys

def apply_migration():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Starting comprehensive migration for multi-admin permissions...")
        
        try:
            # 1. Create the teamrole Enum type if it doesn't exist
            # Note: We need to use EXECUTE outside of a transaction or handle it separately for ENUMs in some PG versions
            # but Postgres usually allows it in transactions.
            print("Checking if 'teamrole' ENUM exists...")
            check_enum = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'teamrole'")).fetchone()
            if not check_enum:
                print("Creating 'teamrole' ENUM...")
                conn.execute(text("CREATE TYPE teamrole AS ENUM ('MEMBER', 'ADMIN')"))
                conn.commit()
            else:
                print("'teamrole' ENUM already exists.")

            # 2. Add 'role' column to user_team_association
            print("Checking if 'role' column exists in 'user_team_association'...")
            check_column = conn.execute(text("""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='user_team_association' AND column_name='role'
            """)).fetchone()
            
            if not check_column:
                print("Adding 'role' column to 'user_team_association'...")
                conn.execute(text("ALTER TABLE user_team_association ADD COLUMN role teamrole NOT NULL DEFAULT 'MEMBER'"))
                conn.commit()
            else:
                print("'role' column already exists in 'user_team_association'.")

            # 3. Backfill ADMIN role from team.owner_id
            print("Promoting current owners to ADMINs...")
            # Check if owner_id still exists to perform the backfill
            check_owner_col = conn.execute(text("""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='team' AND column_name='owner_id'
            """)).fetchone()

            if check_owner_col:
                update_sql = """
                UPDATE user_team_association 
                SET role = 'ADMIN' 
                FROM team 
                WHERE user_team_association.team_id = team.id 
                AND user_team_association.user_id = team.owner_id;
                """
                result = conn.execute(text(update_sql))
                conn.commit()
                print(f"Backfill complete. {result.rowcount} owners promoted to ADMIN.")
                
                # 4. Drop owner_id from team table
                print("Dropping 'owner_id' column from 'team' table...")
                conn.execute(text("ALTER TABLE team DROP COLUMN owner_id"))
                conn.commit()
                print("'owner_id' column removed.")
            else:
                print("'owner_id' column already removed or doesn't exist. Skipping backfill.")

            print("\nMigration successful!")
            
        except Exception as e:
            conn.rollback()
            print(f"\nMigration failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    apply_migration()
