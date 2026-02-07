"""
Verify that all required columns exist in the database.
This script checks if the database schema matches the SQLAlchemy models.
"""
import sys
from sqlalchemy import text, inspect
from backend.db.session import engine


def verify_schema():
    """Verify that all required columns exist in the database."""
    print("Verifying database schema...")
    
    required_columns = {
        "user_team_association": ["user_id", "team_id", "status", "role"],
        "add_on": ["id", "user_id", "game_id", "time", "amount", "status"],
        "cash_out": ["id", "user_id", "game_id", "time", "amount", "status"],
        "user_game_association": ["user_id", "game_id", "status"],
    }
    
    inspector = inspect(engine)
    all_good = True
    
    for table_name, required_cols in required_columns.items():
        print(f"\nChecking table '{table_name}'...")
        
        if not inspector.has_table(table_name):
            print(f"  ❌ Table '{table_name}' does not exist!")
            all_good = False
            continue
            
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        for col in required_cols:
            if col in columns:
                print(f"  ✓ Column '{col}' exists")
            else:
                print(f"  ❌ Column '{col}' is MISSING!")
                all_good = False
    
    print("\n" + "="*60)
    if all_good:
        print("✅ All required columns are present!")
        print("="*60)
        return True
    else:
        print("❌ Some columns are missing. Run the migration script:")
        print("   poetry run python backend/db/tools/add_missing_columns.py")
        print("="*60)
        return False


if __name__ == "__main__":
    try:
        success = verify_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
