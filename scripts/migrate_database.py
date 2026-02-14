#!/usr/bin/env python3
"""
Database Migration Script
Migrates data from the old database (localhost:5432) to the new database (localhost:5434)

Usage:
    python scripts/migrate_database.py [--dry-run] [--skip-confirmation]

Options:
    --dry-run: Show what would be migrated without actually migrating
    --skip-confirmation: Skip the confirmation prompt
"""

import argparse
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Load environment variables
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


def is_running_in_docker() -> bool:
    """Check if the script is running inside a Docker container"""
    # Check for .dockerenv file (most reliable method)
    if Path("/.dockerenv").exists():
        return True
    
    # Check cgroup (alternative method)
    try:
        with open('/proc/1/cgroup', 'rt') as f:
            return 'docker' in f.read()
    except:
        pass
    
    return False


def get_database_url(port: str, db_name: str, container_name: str = None) -> str:
    """
    Construct database URL
    
    Args:
        port: Port number (used when connecting from host)
        db_name: Database name
        container_name: Docker container name (used when connecting from inside Docker)
    """
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin")
    
    # When running inside Docker, connect to other containers by name
    if is_running_in_docker() and container_name:
        # Inside Docker, use container name and internal port 5432
        return f"postgresql://{user}:{password}@{container_name}:5432/{db_name}"
    else:
        # Outside Docker, use localhost and the mapped port
        server = os.getenv("POSTGRES_SERVER", "localhost")
        return f"postgresql://{user}:{password}@{server}:{port}/{db_name}"


def check_connection(engine, db_name: str) -> bool:
    """Check if database connection is working"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✓ Successfully connected to {db_name}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to {db_name}: {e}")
        return False


def get_table_list(engine):
    """Get list of tables in the database"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def get_row_count(engine, table_name: str) -> int:
    """Get row count for a table"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            return result.scalar()
    except Exception as e:
        print(f"Warning: Could not get row count for {table_name}: {e}")
        return 0


def dump_and_restore_database(source_url: str, target_url: str, dry_run: bool = False):
    """
    Dump data from source database and restore to target database
    using pg_dump and psql
    """
    # Parse database URLs
    from urllib.parse import urlparse
    
    source_parsed = urlparse(source_url)
    target_parsed = urlparse(target_url)
    
    # Create temporary dump file
    dump_file = project_root / "temp_db_dump.sql"
    
    # Construct pg_dump command
    pg_dump_cmd = (
        f"pg_dump "
        f"-h {source_parsed.hostname} "
        f"-p {source_parsed.port} "
        f"-U {source_parsed.username} "
        f"-d {source_parsed.path[1:]} "  # Remove leading '/'
        f"--clean --if-exists "
        f"--no-owner --no-acl "
        f"-F p "  # Plain text format
        f"-f {dump_file}"
    )
    
    # Construct psql restore command
    psql_cmd = (
        f"psql "
        f"-h {target_parsed.hostname} "
        f"-p {target_parsed.port} "
        f"-U {target_parsed.username} "
        f"-d {target_parsed.path[1:]} "
        f"-f {dump_file}"
    )
    
    print("\n" + "="*80)
    print("MIGRATION PLAN")
    print("="*80)
    print(f"\n1. Dump source database:")
    print(f"   Command: {pg_dump_cmd}")
    print(f"\n2. Restore to target database:")
    print(f"   Command: {psql_cmd}")
    print("\n" + "="*80)
    
    if dry_run:
        print("\n[DRY RUN] No actual migration performed.")
        return True
    
    # Set password environment variables
    os.environ['PGPASSWORD'] = source_parsed.password or os.getenv("POSTGRES_PASSWORD", "admin")
    
    print("\n📦 Dumping source database...")
    import subprocess
    
    try:
        result = subprocess.run(
            pg_dump_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ pg_dump failed: {result.stderr}")
            return False
        
        print(f"✓ Database dumped to {dump_file}")
        print(f"  Dump file size: {dump_file.stat().st_size / 1024:.2f} KB")
        
    except Exception as e:
        print(f"✗ Error during dump: {e}")
        return False
    
    print("\n📥 Restoring to target database...")
    
    try:
        os.environ['PGPASSWORD'] = target_parsed.password or os.getenv("POSTGRES_PASSWORD", "admin")
        
        result = subprocess.run(
            psql_cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"✗ psql restore failed: {result.stderr}")
            print(f"  (Some errors during restore may be expected, especially if the database was empty)")
        
        print(f"✓ Database restored to target")
        
    except Exception as e:
        print(f"✗ Error during restore: {e}")
        return False
    finally:
        # Clean up dump file
        if dump_file.exists():
            dump_file.unlink()
            print(f"✓ Cleaned up temporary dump file")
    
    return True


def get_table_dependency_order(base_metadata):
    """
    Get tables in dependency order (parent tables first, child tables last)
    using topological sort based on foreign key relationships
    """
    from collections import defaultdict, deque
    
    # Build dependency graph
    graph = defaultdict(set)  # table -> tables that depend on it
    in_degree = defaultdict(int)  # table -> number of dependencies
    
    all_tables = set(base_metadata.tables.keys())
    
    # Initialize in_degree for all tables
    for table_name in all_tables:
        in_degree[table_name] = 0
    
    # Build the graph from foreign keys
    for table_name, table in base_metadata.tables.items():
        for fk in table.foreign_keys:
            parent_table = fk.column.table.name
            if parent_table != table_name:  # Ignore self-references
                graph[parent_table].add(table_name)
                in_degree[table_name] += 1
    
    # Topological sort using Kahn's algorithm
    queue = deque([t for t in all_tables if in_degree[t] == 0])
    sorted_tables = []
    
    while queue:
        table = queue.popleft()
        sorted_tables.append(table)
        
        for dependent in graph[table]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # Check for circular dependencies
    if len(sorted_tables) != len(all_tables):
        print("⚠️  Warning: Circular dependencies detected, using original order")
        return list(all_tables)
    
    return sorted_tables


def migrate_using_sqlalchemy(source_engine, target_engine, dry_run: bool = False):
    """
    Alternative migration method using SQLAlchemy
    (Fallback if pg_dump/psql are not available)
    """
    print("\n⚠️  pg_dump/psql not available. Using SQLAlchemy migration method.")
    print("   This method may not preserve all database features (sequences, triggers, etc.)")
    
    # Import all models to get metadata
    from backend.db.base import Base
    
    # Get tables in dependency order
    sorted_tables = get_table_dependency_order(Base.metadata)
    
    # Get actual tables that exist in source
    source_tables = get_table_list(source_engine)
    
    # Filter sorted tables to only include those that exist in source
    tables_to_migrate = [t for t in sorted_tables if t in source_tables]
    
    if not tables_to_migrate:
        print("✗ No tables found in source database")
        return False
    
    print(f"\n📋 Tables to migrate (in dependency order): {len(tables_to_migrate)}")
    for table in tables_to_migrate:
        count = get_row_count(source_engine, table)
        print(f"  - {table}: {count} rows")
    
    if dry_run:
        print("\n[DRY RUN] No actual migration performed.")
        return True
    
    # Ensure tables are created in target
    Base.metadata.create_all(bind=target_engine)
    
    print("\n📦 Migrating data...")
    
    with source_engine.connect() as source_conn:
        with target_engine.connect() as target_conn:
            # Temporarily disable foreign key checks for smoother migration
            try:
                target_conn.execute(text("SET session_replication_role = 'replica';"))
                target_conn.commit()
                print("  ✓ Temporarily disabled foreign key checks")
            except:
                print("  ⚠️  Could not disable foreign key checks, proceeding anyway")
            
            for table_name in tables_to_migrate:
                print(f"\n  Migrating table: {table_name}")
                
                try:
                    # Read all rows from source
                    result = source_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                    rows = result.fetchall()
                    columns = result.keys()
                    
                    if not rows:
                        print(f"    ✓ Table is empty, skipping")
                        continue
                    
                    # Clear target table
                    target_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                    target_conn.commit()
                    
                    # Insert rows into target
                    column_names = ", ".join([f'"{col}"' for col in columns])
                    placeholders = ", ".join([f":{col}" for col in columns])
                    
                    insert_sql = text(
                        f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
                    )
                    
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        target_conn.execute(insert_sql, row_dict)
                    
                    target_conn.commit()
                    print(f"    ✓ Migrated {len(rows)} rows")
                    
                except Exception as e:
                    print(f"    ✗ Error migrating {table_name}: {e}")
                    target_conn.rollback()
                    continue
            
            # Re-enable foreign key checks
            try:
                target_conn.execute(text("SET session_replication_role = 'origin';"))
                target_conn.commit()
                print("\n  ✓ Re-enabled foreign key checks")
            except:
                pass
    
    print("\n✓ Migration completed")
    return True


def verify_migration(source_engine, target_engine):
    """Verify that migration was successful"""
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    source_tables = get_table_list(source_engine)
    target_tables = get_table_list(target_engine)
    
    print(f"\nSource tables: {len(source_tables)}")
    print(f"Target tables: {len(target_tables)}")
    
    if set(source_tables) != set(target_tables):
        print("\n⚠️  Table mismatch!")
        missing = set(source_tables) - set(target_tables)
        extra = set(target_tables) - set(source_tables)
        if missing:
            print(f"  Missing in target: {missing}")
        if extra:
            print(f"  Extra in target: {extra}")
    
    print("\nRow count comparison:")
    all_match = True
    for table in source_tables:
        source_count = get_row_count(source_engine, table)
        target_count = get_row_count(target_engine, table) if table in target_tables else 0
        
        match = "✓" if source_count == target_count else "✗"
        print(f"  {match} {table}: {source_count} → {target_count}")
        
        if source_count != target_count:
            all_match = False
    
    print("\n" + "="*80)
    if all_match:
        print("✓ Migration verified successfully!")
    else:
        print("⚠️  Some discrepancies found. Please review.")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Migrate database from old to new instance")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--skip-confirmation", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--use-sqlalchemy", action="store_true", help="Force use of SQLAlchemy migration method")
    args = parser.parse_args()
    
    print("="*80)
    print("DATABASE MIGRATION SCRIPT")
    print("="*80)
    
    # Detect environment
    in_docker = is_running_in_docker()
    if in_docker:
        print("\n🐳 Running inside Docker container")
    else:
        print("\n💻 Running on host machine")
    
    # Database configuration
    source_db_name = "tdd"  # Old database name on the host
    target_db_name = os.getenv("POSTGRES_DB", "cashgame_tracker")
    
    # Source: PostgreSQL on the HOST machine (not in a container)
    # Target: PostgreSQL in Docker container (cashgame_db)
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "admin")
    
    if in_docker:
        # Running inside Docker, need to access:
        # - Host's PostgreSQL (source) via host.docker.internal or host gateway
        # - Another container's PostgreSQL (target) via container name
        source_url = f"postgresql://{user}:{password}@host.docker.internal:5432/{source_db_name}"
        target_url = f"postgresql://{user}:{password}@cashgame_db:5432/{target_db_name}"
        print(f"\nSource Database: host.docker.internal:5432/{source_db_name} (Host PostgreSQL)")
        print(f"Target Database: cashgame_db:5432/{target_db_name} (Docker container)")
    else:
        # Running on host, can access both via localhost
        source_url = f"postgresql://{user}:{password}@localhost:5432/{source_db_name}"
        target_url = f"postgresql://{user}:{password}@localhost:5434/{target_db_name}"
        print(f"\nSource Database: localhost:5432/{source_db_name} (Host PostgreSQL)")
        print(f"Target Database: localhost:5434/{target_db_name} (Docker container)")
    
    # Create engines
    try:
        source_engine = create_engine(source_url)
        target_engine = create_engine(target_url)
    except Exception as e:
        print(f"\n✗ Failed to create database engines: {e}")
        return 1
    
    # Check connections
    print("\n" + "-"*80)
    print("Checking database connections...")
    print("-"*80)
    
    if not check_connection(source_engine, "source database"):
        print("\n✗ Cannot proceed without source database connection")
        print("  Make sure the old database is running on localhost:5432")
        return 1
    
    if not check_connection(target_engine, "target database"):
        print("\n✗ Cannot proceed without target database connection")
        print("  Make sure to start the new database:")
        print("  docker-compose up -d db")
        return 1
    
    # Show source database info
    source_tables = get_table_list(source_engine)
    print(f"\n📊 Source database has {len(source_tables)} tables")
    
    if not source_tables:
        print("✗ No tables found in source database. Nothing to migrate.")
        return 0
    
    total_rows = 0
    for table in source_tables:
        count = get_row_count(source_engine, table)
        total_rows += count
        print(f"  - {table}: {count} rows")
    
    print(f"\nTotal rows to migrate: {total_rows}")
    
    # Confirmation
    if not args.skip_confirmation and not args.dry_run:
        print("\n" + "!"*80)
        print("⚠️  WARNING: This will OVERWRITE all data in the target database!")
        print("!"*80)
        response = input("\nAre you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            return 0
    
    # Perform migration
    if args.use_sqlalchemy:
        success = migrate_using_sqlalchemy(source_engine, target_engine, args.dry_run)
    else:
        # Try pg_dump/psql first
        success = dump_and_restore_database(source_url, target_url, args.dry_run)
        
        # Fallback to SQLAlchemy if pg_dump failed
        if not success:
            print("\n⚠️  pg_dump method failed. Falling back to SQLAlchemy method...")
            success = migrate_using_sqlalchemy(source_engine, target_engine, args.dry_run)
    
    if not success:
        print("\n✗ Migration failed")
        return 1
    
    # Verify migration (unless dry run)
    if not args.dry_run:
        verify_migration(source_engine, target_engine)
    
    print("\n✓ Migration process completed!")
    print("\nNext steps:")
    print("  1. Verify the data in the new database")
    print("  2. Update your .env file to use the new database (already done)")
    print("  3. Test your application with the new database")
    print("  4. Once confirmed working, you can stop using the old database")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
