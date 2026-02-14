#!/usr/bin/env python3
"""
Quick setup script for the new database
"""

import os
import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, shell=True, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=shell, check=check, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_docker():
    """Check if Docker is running"""
    success, _, _ = run_command("docker ps", check=False)
    return success

def main():
    print("="*80)
    print("CASH GAME TRACKER - DATABASE SETUP")
    print("="*80)
    
    # Check if Docker is running
    print("\n1. Checking Docker...")
    if not check_docker():
        print("   ✗ Docker is not running!")
        print("   Please start Docker Desktop and try again.")
        return 1
    print("   ✓ Docker is running")
    
    # Check if .env.docker exists
    print("\n2. Checking .env.docker...")
    if not Path(".env.docker").exists():
        print("   ⚠️  .env.docker not found!")
        print("   Creating from template...")
        
        if Path(".env.docker.template").exists():
            # Copy template and update with real credentials from .env
            with open(".env") as f:
                env_content = f.read()
            with open(".env.docker.template") as f:
                template = f.read()
            
            # Extract credentials from .env
            lines = []
            for line in env_content.split('\n'):
                if any(key in line for key in ['MAIL_PASSWORD=', 'GOOGLE_CLIENT_ID=', 'GOOGLE_CLIENT_SECRET=']):
                    lines.append(line)
            
            # Update template
            with open(".env.docker", "w") as f:
                f.write(template)
                if lines:
                    f.write("\n# Auto-updated from .env:\n")
                    for line in lines:
                        f.write(line + "\n")
            
            print("   ✓ Created .env.docker from template")
        else:
            print("   ✗ Template not found!")
            return 1
    else:
        print("   ✓ .env.docker exists")
    
    # Start the database container
    print("\n3. Starting database container...")
    success, stdout, stderr = run_command("docker-compose up -d db", check=False)
    if not success:
        print(f"   ✗ Failed to start database: {stderr}")
        return 1
    print("   ✓ Database container started")
    
    # Wait for database to be healthy
    print("\n4. Waiting for database to be ready...")
    for i in range(30):
        success, stdout, stderr = run_command(
            'docker-compose ps --format json db',
            check=False
        )
        if success and 'healthy' in stdout.lower():
            print("   ✓ Database is ready")
            break
        time.sleep(1)
        if i % 5 == 0 and i > 0:
            print(f"   Still waiting... ({i}s)")
    else:
        print("   ⚠️  Database might not be fully healthy yet, but continuing...")
    
    # Ask if user wants to migrate data
    print("\n5. Data migration")
    print("   Do you want to migrate data from the old database (localhost:5433)?")
    print("   (yes/no/later): ", end='')
    
    response = input().lower().strip()
    
    if response == 'yes':
        print("\n   Running migration script...")
        result = subprocess.run([sys.executable, "scripts/migrate_database.py"])
        if result.returncode != 0:
            print("   ⚠️  Migration had issues. Please review the output above.")
        else:
            print("   ✓ Migration completed")
    elif response == 'later':
        print("\n   Skipped for now. You can run the migration later with:")
        print("   python scripts/migrate_database.py")
    else:
        print("\n   Skipped. Starting with a fresh database.")
    
    # Summary
    print("\n" + "="*80)
    print("SETUP COMPLETE!")
    print("="*80)
    print("\nDatabase is running at: localhost:5434")
    print("Database name: cashgame_tracker")
    print("\nNext steps:")
    print("  • Test locally: just start_local")
    print("  • Or run full Docker stack: docker-compose up -d")
    print("\nFor more information, see: docs/DATABASE_MIGRATION.md")
    print("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
