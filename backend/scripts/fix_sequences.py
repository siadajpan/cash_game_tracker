import sys
import os

# Add the project root to the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from sqlalchemy import text
from backend.db.session import engine

def fix_sequences():
    """
    Fixes the PostgreSQL sequences for tables that might be out of sync 
    after manual data migration or insertion with explicit headers.
    """
    print("Starting sequence fix...")
    
    # List of tables that use auto-increment integer primary keys
    tables = [
        "user", 
        "team", 
        "game", 
        "buy_in", 
        "add_on", 
        "cash_out", 
        "chip_structure",
        "chip", 
        "chip_amount",
        "user_verifications"
    ]
    
    with engine.connect() as conn:
        for table in tables:
            try:
                # Construct the sequence name (standard PostgreSQL convention)
                # If your sequences are named differently, you'll need to query information_schema
                seq_name = f"{table}_id_seq"
                # For user_verifications, sequence might be user_verifications_id_seq
                
                # get max id
                # We quote table names in case of reserved words (like 'user' in some SQL dialects, though PG is fine usually)
                query = text(f'SELECT MAX(id) FROM "{table}"')
                result = conn.execute(query)
                max_id = result.scalar()
                
                if max_id is None:
                    max_id = 0
                
                # Set the sequence
                # setval('seq', max_id, true) -> next is max_id + 1
                
                print(f"Fixing {table}: max_id={max_id}")
                
                if max_id == 0:
                     conn.execute(text(f"SELECT setval('{seq_name}', 1, false)"))
                else:
                     conn.execute(text(f"SELECT setval('{seq_name}', {max_id}, true)"))
                
                print(f"  -> Sequence {seq_name} reset to {max_id}")
                
            except Exception as e:
                print(f"Error fixing {table}: {e}")
                # Don't stop, try other tables
                
        conn.commit()
    print("Sequence fix complete.")

if __name__ == "__main__":
    fix_sequences()
