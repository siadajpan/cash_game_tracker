from backend.db.session import engine
from sqlalchemy import inspect

inspector = inspect(engine)
print("Database:", engine.url)
print("Tables found in DB:", inspector.get_table_names(schema="public"))