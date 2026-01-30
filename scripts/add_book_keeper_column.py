import sys
import os
from sqlalchemy import text

# Add the parent directory to sys.path to allow imports from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import engine

def run_migration():
    print("Starting migration: Adding book_keeper_id to game table...")
    
    with engine.connect() as connection:
        # Begin transaction
        with connection.begin():
            try:
                # Add column
                print("Adding column 'book_keeper_id'...")
                connection.execute(text('ALTER TABLE game ADD COLUMN book_keeper_id INTEGER;'))
                
                # Add Foreign Key
                print("Adding foreign key constraint...")
                connection.execute(text('ALTER TABLE game ADD CONSTRAINT fk_game_book_keeper_id_user FOREIGN KEY (book_keeper_id) REFERENCES "user" (id);'))
                
                print("Migration completed successfully.")
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Migration failed. The column might already exist.")

if __name__ == "__main__":
    run_migration()
