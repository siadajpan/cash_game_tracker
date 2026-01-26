import sys
import os
import argparse
from datetime import datetime
from typing import List

# Ensure backend modules can be imported
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
import backend.db.base  # Register all models
from backend.db.models.user import User
from backend.db.models.team import Team
from backend.db.models.game import Game
from backend.db.models.user_team import UserTeam
from backend.db.models.user_game import UserGame
from backend.db.models.buy_in import BuyIn
from backend.db.models.cash_out import CashOut
from backend.db.models.add_on import AddOn
from backend.db.models.user_verification import UserVerification
from backend.db.models.player_request_status import PlayerRequestStatus
from backend.core.hashing import Hasher
from backend.db.repository.team import create_new_team
from backend.schemas.team import TeamCreate

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def parse_legacy_file(filepath: str):
    import pandas as pd
    import re
    from datetime import timedelta

    # Read all sheets from ODS file to find the one with "data"
    try:
        sheets = pd.read_excel(filepath, engine="odf", sheet_name=None, header=None)
    except Exception as e:
        print(f"Error reading ODS file: {e}")
        return [], []

    df = None
    header_row_idx = None
    header_col_idx = None
    
    # search for "data" in any sheet
    for sheet_name, sheet_df in sheets.items():
        print(f"Scanning sheet '{sheet_name}'...")
        # Scan first 20 rows and 20 cols
        for r in range(min(20, len(sheet_df))):
            for c in range(min(20, len(sheet_df.columns))):
                val = str(sheet_df.iat[r, c]).strip().lower()
                if val == "data":
                    df = sheet_df
                    header_row_idx = r
                    header_col_idx = c
                    print(f"Found 'data' header in sheet '{sheet_name}' at row {r}, col {c}")
                    break
            if header_row_idx is not None: break
        if header_row_idx is not None: break
            
    if df is None:
        print("Could not find cell 'data' in any sheet (checked first 20x20 cells)")
        return [], []
        
    # Parse Header
    header_row = df.iloc[header_row_idx]
    players = []
    player_indices = {} # col_idx -> nick
    
    # Players start 2 columns after "data" column
    # e.g. B1="data", C1="", D1="Radek"...
    start_col = header_col_idx + 2
    
    for c in range(start_col, len(header_row)):
        val = header_row[c]
        if pd.notna(val) and str(val).strip():
             nick = str(val).strip()
             # Skip statistics columns
             if nick.lower() in ['bilans', 'ilość osób', 'ilosc osob']:
                 continue
                 
             players.append(nick)
             player_indices[c] = nick
             
    print(f"Found {len(players)} players: {players}")
    
    games_data = []
    
    num_rows = len(df)
    current_idx = header_row_idx + 1
    
    while current_idx < num_rows:
        row = df.iloc[current_idx]
        
        # Check column at header_col_idx - 1 for Game Index (Number)
        # If header is at 0, maybe number is not present or at 0? 
        # But user format: 1 (Col A), Data (Col B). so Data=1.
        
        search_col = header_col_idx - 1 if header_col_idx > 0 else 0
        idx_val = row[search_col]
        
        is_game_start = False
        try:
            if pd.notna(idx_val):
                s = str(idx_val).strip()
                # Check if it looks like an integer (1, 2, 3...)
                if s.replace('.0', '').isdigit(): 
                    is_game_start = True
        except:
            pass
            
        if not is_game_start:
            # Found end of data (statistics or empty)
            print(f"Stopping analysis at row {current_idx} (found non-numeric index '{idx_val}').")
            break
            
        # This is a game row (Buy In row)
        # Next row should be Balance/Profit row
        if current_idx + 1 >= num_rows:
            break
            
        row_buyin = row
        row_balance = df.iloc[current_idx + 1]
        
        # Date info is in "data" column (header_col_idx)
        # "Radek śr16.06.2021"
        game_info_raw = str(row_buyin[header_col_idx])
        
        # Date regex: allow 1 or 2 digits for day/month, and tolerate multiple dots (typo "..")
        date_match = re.search(r'(\d{1,2}\.+\d{1,2}\.+\d{4})', game_info_raw)
        if not date_match:
            print(f"Skipping row {current_idx}, no date found in '{game_info_raw}'")
            current_idx += 1
            continue
            
        date_str = date_match.group(1).replace("..", ".")
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            print(f"Skipping row {current_idx}, invalid date format in '{date_str}'")
            current_idx += 1
            continue

        date_iso = dt.date().isoformat()
        
        # Times: 20:00 to 01:00 next day
        start_time = dt.replace(hour=20, minute=0, second=0)
        finish_time = start_time + timedelta(hours=5)
        
        game_record = {
            "date": date_iso,
            "start_time": start_time,
            "finish_time": finish_time,
            "player_stats": []
        }
        
        for col_idx, nick in player_indices.items():
            # Buy In
            buy_in = 0.0
            raw_bi = row_buyin[col_idx] if col_idx < len(row_buyin) else None
            
            # Balance
            balance = 0.0
            raw_bal = row_balance[col_idx] if col_idx < len(row_balance) else None
            
            def parse_val(v):
                if pd.isna(v): return None
                s = str(v).strip().lower()
                if s == 'x' or s == '': return None
                try:
                    return float(v)
                except:
                    return None
            
            bi_val = parse_val(raw_bi)
            
            if bi_val is not None:
                buy_in = bi_val
                bal_val = parse_val(raw_bal)
                if bal_val is not None:
                    balance = bal_val
                
                cash_out = buy_in + balance
                game_record["player_stats"].append({
                    "nick": nick,
                    "buy_in": buy_in,
                    "cash_out": cash_out
                })
        
        games_data.append(game_record)
        current_idx += 2 
        
    return players, games_data

def get_or_create_user(db: Session, email: str, nick: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"Found existing admin user: {user.nick} ({user.email})")
        return user
    
    print(f"Creating new admin user: {nick} ({email})")
    new_user = User(
        email=email,
        nick=nick,
        hashed_password=Hasher.get_password_hash("admin123"), # Default password
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_or_create_team(db: Session, user: User, team_name: str) -> Team:
    # Check if user already has this team
    for t in user.teams:
        if t.name == team_name:
            print(f"Found existing team: {t.name}")
            return t
            
    # Try to find team globally by name? Or creates new unique one? 
    # Team names might be unique or per user. Assuming creating new if not in user's list.
    print(f"Creating new team: {team_name}")
    import random
    # Generate random numeric code like "1234"
    code = str(random.randint(1000, 9999))
    new_team = create_new_team(TeamCreate(name=team_name, search_code=code), user, db)
    return new_team

def run_import(file_path: str, admin_nick: str, admin_email: str, team_name: str):
    db = SessionLocal()
    
    # 1. Get/Create Admin User
    admin_user = get_or_create_user(db, admin_email, admin_nick)
    
    # 2. Get/Create Team
    team = get_or_create_team(db, admin_user, team_name)
    
    # 3. Parse File
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    players_list, games_records = parse_legacy_file(file_path)
    print(f"Parsed {len(games_records)} games from file.")

    # 4. Map Users
    user_map = {} # Nick -> User Object
    
    for nick in players_list:
        if nick == admin_nick:
            # Map column to admin user
            print(f"Mapping column '{nick}' to Admin User")
            user_map[nick] = admin_user
            # Ensure admin is in team (create_new_team handles it, but safety check)
            if admin_user not in team.users:
                ut = UserTeam(
                    user_id=admin_user.id, 
                    team_id=team.id, 
                    status=PlayerRequestStatus.APPROVED
                )
                db.add(ut)
                db.commit()
        else:
            # Guest or existing guest
            # Check by nick first? Or construct guest email
            # We construct guest email to be unique-ish
            guest_email = f"{nick.lower().replace(' ', '_')}@legacy.import"
            
            # Check if exists by email strictly to avoid collision with real users
            guest_user = db.query(User).filter(User.email == guest_email).first()
            
            if not guest_user:
                # Fallback: check by nick? If a real user named "Marc" exists, do we claim him?
                # Safer to create specific legacy guest to avoid messing up real accounts.
                print(f"Creating guest user: {nick}")
                guest_user = User(
                    email=guest_email,
                    nick=nick,
                    hashed_password=Hasher.get_password_hash("guest123"),
                    is_active=True
                )
                db.add(guest_user)
                db.commit()
                db.refresh(guest_user)
            else:
                print(f"Found existing guest: {nick}")
                
            # Add to team if not present
            if guest_user not in team.users:
                ut = UserTeam(
                    user_id=guest_user.id, 
                    team_id=team.id,
                    status=PlayerRequestStatus.APPROVED
                )
                db.add(ut)
                db.commit()
            
            user_map[nick] = guest_user

    # 5. Insert Games
    created_count = 0
    for g_rec in games_records:
        # Check duplicate game? Same date, same team?
        # For now, just import.
        
        print(f"Importing game {g_rec['date']}...")
        new_game = Game(
            date=g_rec['date'],
            start_time=g_rec['start_time'],
            finish_time=g_rec['finish_time'],
            default_buy_in=0,
            running=False,
            owner_id=admin_user.id,
            team_id=team.id,
            chip_structure_id=None
        )
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
        
        for p_stat in g_rec['player_stats']:
            player = user_map[p_stat['nick']]
            
            # Associate User to Game
            if player not in new_game.players:
                ug = UserGame(user_id=player.id, game_id=new_game.id)
                db.add(ug)
                db.commit()
                
            # Buy In
            buy_in = BuyIn(
                amount=p_stat['buy_in'],
                user_id=player.id,
                game_id=new_game.id,
                time=new_game.start_time
            )
            db.add(buy_in)
            
            # Cash Out
            cash_out = CashOut(
                amount=p_stat['cash_out'],
                user_id=player.id,
                game_id=new_game.id,
                time=new_game.finish_time,
                status=PlayerRequestStatus.APPROVED
            )
            db.add(cash_out)
        
        db.commit()
        created_count += 1

    print(f"Successfully imported {created_count} games into Team '{team.name}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import legacy games from spreadsheet dump.")
    parser.add_argument("file", help="Path to the legacy data file")
    parser.add_argument("--nick", required=True, help="Admin user nickname")
    parser.add_argument("--email", required=True, help="Admin user email")
    parser.add_argument("--team", required=True, help="Team name to import games into")
    
    # parser.add_argument("--max-row", type=int, default=706, help="Stop analysis at this row number (default: 706)")
    
    args = parser.parse_args()
    
    run_import(args.file, args.nick, args.email, args.team)
