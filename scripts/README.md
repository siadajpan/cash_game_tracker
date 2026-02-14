# Database Management Scripts

This directory contains scripts for managing your cash game tracker database.

## Setup & Migration

### `setup_database.py` - Quick Setup (Recommended)
Interactive script that sets up everything for you.

```bash
python scripts/setup_database.py
```

**What it does:**
- ✓ Checks if Docker is running
- ✓ Creates `.env.docker` if needed
- ✓ Starts the database container
- ✓ Optionally runs the migration

### `migrate_database.py` - Data Migration
Migrates data from the old database (localhost:5433) to the new one (localhost:5434).

```bash
# Dry run (see what will happen without doing it)
python scripts/migrate_database.py --dry-run

# Actual migration
python scripts/migrate_database.py

# Skip confirmation prompt
python scripts/migrate_database.py --skip-confirmation

# Force SQLAlchemy method (if pg_dump fails)
python scripts/migrate_database.py --use-sqlalchemy
```

**What it does:**
- ✓ Dumps data from old database
- ✓ Restores to new database
- ✓ Verifies migration was successful
- ✓ Shows detailed progress

## Diagnostics

### `check_databases.py` - Connection Check
Tests connectivity to both old and new databases.

```bash
python scripts/check_databases.py
```

**What it shows:**
- ✓ Connection status for both databases
- ✓ PostgreSQL version
- ✓ Number of tables
- ✓ Sample table names

## Workflow Examples

### First Time Setup
```bash
# 1. Quick setup (recommended)
python scripts/setup_database.py

# 2. Or manual setup
docker-compose up -d db
python scripts/migrate_database.py

# 3. Verify everything works
python scripts/check_databases.py
```

### Troubleshooting
```bash
# Check if databases are accessible
python scripts/check_databases.py

# Test migration without actually doing it
python scripts/migrate_database.py --dry-run

# Force alternative migration method
python scripts/migrate_database.py --use-sqlalchemy
```

### Regular Operations
```bash
# Start database only
docker-compose up -d db

# Start entire application
docker-compose up -d

# View logs
docker-compose logs -f db

# Stop everything
docker-compose down

# Stop and remove volumes (careful!)
docker-compose down -v
```

## Environment Files

The scripts use these environment files:

- **`.env`** - For local development (POSTGRES_SERVER=localhost, POSTGRES_PORT=5434)
- **`.env.docker`** - For Docker deployment (POSTGRES_SERVER=db, POSTGRES_PORT=5432)

## Need Help?

See the complete documentation:
- **Setup guide**: `docs/DATABASE_MIGRATION.md`
- **Summary**: `docs/DATABASE_SEPARATION_SUMMARY.md`
