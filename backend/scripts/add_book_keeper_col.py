from backend.db.session import engine
from sqlalchemy import text

def add_book_keeper_column():
    with engine.connect() as conn:
        try:
            conn.execute(text('ALTER TABLE game ADD COLUMN book_keeper_id INTEGER REFERENCES "user"(id)'))
            conn.commit()
            print("Successfully added book_keeper_id column to game table.")
        except Exception as e:
            print(f"Error adding column (might already exist): {e}")

if __name__ == "__main__":
    add_book_keeper_column()
