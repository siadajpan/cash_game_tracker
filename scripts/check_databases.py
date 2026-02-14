#!/usr/bin/env python3
"""
Quick database connectivity checker
Tests connections to both old and new databases
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


def test_connection(db_name: str, host: str, port: str, db: str):
    """Test a database connection"""
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin")
    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    print(f"\nTesting {db_name}:")
    print(f"  URL: {host}:{port}/{db}")
    
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            
            # Count tables
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ))
            table_count = result.scalar()
            
            print(f"  ✓ Connection successful")
            print(f"  ✓ PostgreSQL version: {version.split(',')[0]}")
            print(f"  ✓ Tables: {table_count}")
            
            # Show some table names
            if table_count > 0:
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name LIMIT 5"
                ))
                tables = [row[0] for row in result]
                print(f"  ✓ Sample tables: {', '.join(tables)}")
            
            return True
            
    except Exception as e:
        print(f"  ✗ Connection failed: {str(e)[:100]}")
        return False


def main():
    print("="*80)
    print("DATABASE CONNECTIVITY CHECK")
    print("="*80)
    
    # Test old database (shared with no_pain app)
    old_success = test_connection(
        "Old Database (shared)",
        "localhost",
        "5433",
        "tdd"
    )
    
    # Test new database
    new_success = test_connection(
        "New Database (cash tracker)",
        "localhost",
        "5434",
        os.getenv("POSTGRES_DB", "cashgame_tracker")
    )
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if old_success:
        print("✓ Old database (localhost:5433) is accessible")
    else:
        print("✗ Old database (localhost:5433) is NOT accessible")
        print("  (This is okay if you've already migrated)")
    
    if new_success:
        print("✓ New database (localhost:5434) is accessible and ready!")
    else:
        print("✗ New database (localhost:5434) is NOT accessible")
        print("  Please run: docker-compose up -d db")
    
    print("="*80)
    
    if new_success:
        print("\n✓ Your application should work with the new database!")
        return 0
    else:
        print("\n⚠️  New database is not running. Please start it first.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
