
from sqlalchemy import create_engine, text
from backend.core.config import settings

def add_default_chip_structure_column():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Checking if default_chip_structure_id column exists in team table...")
        # Postgres check
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='team' AND column_name='default_chip_structure_id';
        """)).fetchone()
        
        if not result:
            print("Adding default_chip_structure_id column to team table...")
            conn.execute(text("ALTER TABLE team ADD COLUMN default_chip_structure_id INTEGER REFERENCES chip_structure(id);"))
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column already exists.")

if __name__ == "__main__":
    add_default_chip_structure_column()
