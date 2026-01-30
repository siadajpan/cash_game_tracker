
import unicodedata
import os
import sys

# Add the project root to sys.path so we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.db.base import User 

def normalize_nick_to_ascii(string_to_normalize):
    """
    Standardizes a string by:
    1. Converting to lowercase
    2. Explicitly handling Polish 'ł' and 'Ł' (as NFD doesn't decompose them)
    3. Removing other diacritics (dots, tails, etc.)
    4. Replacing spaces with underscores
    """
    if not string_to_normalize:
        return ""
    
    # Handle lowercase and specific Polish L
    val = string_to_normalize.lower().replace('ł', 'l')
    
    # Decompose unicode characters (e.g., 'ż' -> 'z' + dot)
    normalized = unicodedata.normalize('NFD', val)
    
    # Filter out the diacritic marks (category 'Mn') and re-join
    ascii_str = "".join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    return ascii_str.replace(' ', '_')

def fix_overbet_emails():
    db = SessionLocal()
    try:
        # We target all auto-generated guest emails
        users = db.query(User).filter(User.email.like("%@over-bet.com")).all()
        print(f"Found {len(users)} users with @over-bet.com emails.")
        
        updated_count = 0
        for user in users:
            if '@' not in user.email:
                continue
                
            local_part, domain = user.email.split('@')
            
            # The local_part usually contains [nick]_[team_code]
            new_local_part = normalize_nick_to_ascii(local_part)
            new_email = f"{new_local_part}@{domain}"
            
            if new_email != user.email:
                print(f"Updating: {user.email} -> {new_email}")
                user.email = new_email
                updated_count += 1
        
        if updated_count > 0:
            db.commit()
            print(f"Successfully updated and committed {updated_count} users.")
        else:
            print("No emails required updating.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting email normalization script...")
    fix_overbet_emails()
    print("Done.")
