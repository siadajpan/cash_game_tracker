import sys
import os
import argparse
import json
from datetime import datetime

# Ensure we can import from the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
# Ensure we can import backend logic if needed (though we just modify sys path generally for consistency)
sys.path.append(os.getcwd())

try:
    from import_legacy import parse_legacy_file
except ImportError:
    # If run from root, backend.scripts.import_legacy might be needed
    # But simple append logic above should work if both in same dir
    try:
        from backend.scripts.import_legacy import parse_legacy_file
    except ImportError:
        print("Could not import parse_legacy_file. Ensure you are running from project root.")
        sys.exit(1)

def convert_to_json(ods_path, json_output_path):
    print(f"Parsing {ods_path}...")
    # Using existing parser
    players, games_data = parse_legacy_file(ods_path)
    
    formatted_games = []
    
    for g_rec in games_data:
        # Expected format:
        # {
        #   "start_time": "YYYY-MM-DD HH:MM",
        #   "finish_time": "YYYY-MM-DD HH:MM",
        #   "players": [ { "nick": "...", "buy_in": 100.0, "cash_out": 150.0 } ]
        # }
        
        # Original format:
        # {
        #   "date": date_iso,
        #   "start_time": datetime object,
        #   "finish_time": datetime object,
        #   "player_stats": [ ... ]
        # }
        
        start_dt = g_rec["start_time"]
        finish_dt = g_rec["finish_time"]
        
        # Ensure they are datetimes
        if not isinstance(start_dt, datetime):
            # Fallback if parser changes? It currently returns datetime
            pass
            
        game_obj = {
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
            "finish_time": finish_dt.strftime("%Y-%m-%d %H:%M"),
            "players": []
        }
        
        for p_stat in g_rec["player_stats"]:
            player_obj = {
                "nick": p_stat["nick"],
                "buy_in": float(p_stat["buy_in"]),
                "cash_out": float(p_stat["cash_out"])
            }
            game_obj["players"].append(player_obj)
            
        formatted_games.append(game_obj)
        
    print(f"Converted {len(formatted_games)} games.")
    
    with open(json_output_path, "w") as f:
        json.dump(formatted_games, f, indent=2)
        
    print(f"JSON written to {json_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert legacy ODS game history to JSON format for web import.")
    parser.add_argument("ods_file", help="Path to the legacy .ods/.xlsx file")
    parser.add_argument("--output", "-o", default="games_export.json", help="Output JSON filename")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ods_file):
        print(f"Error: File {args.ods_file} not found.")
        sys.exit(1)
        
    convert_to_json(args.ods_file, args.output)
