from sqlalchemy import create_engine, text
from backend.core.config import settings

def migrate_owners_to_admins():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Promoting current owners to ADMINs...")
        try:
            # Update UserTeam where user is the owner of the team
            # We match team.owner_id with user_team_association.user_id
            sql = """
            UPDATE user_team_association 
            SET role = 'ADMIN' 
            FROM team 
            WHERE user_team_association.team_id = team.id 
            AND user_team_association.user_id = team.owner_id;
            """
            result = conn.execute(text(sql))
            conn.commit()
            print(f"Migration complete. {result.rowcount} owners promoted to ADMIN.")
        except Exception as e:
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate_owners_to_admins()
