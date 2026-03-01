import sqlite3

def run():
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    # Check if table exists
    cursor.execute("PRAGMA table_info(user)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'email' in columns:
        print("Renaming email to nick_id in user table")
        try:
            cursor.execute("ALTER TABLE user RENAME COLUMN email TO nick_id")
            conn.commit()
            print("Successfully renamed.")
        except Exception as e:
            print("Error renaming:", e)
    else:
        print("Column 'email' not found or already renamed.")
        
    conn.close()

if __name__ == '__main__':
    run()
