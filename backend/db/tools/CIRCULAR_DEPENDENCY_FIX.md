# CIRCULAR DEPENDENCY FIX - Quick Guide

## Problem
The `team` and `chip_structure` tables have circular foreign key dependencies:
- `chip_structure.team_id` → `team.id`
- `team.default_chip_structure_id` → `chip_structure.id`

This prevents SQLAlchemy from determining the correct order to drop tables.

## Solutions (in order of preference)

### Solution 1: Use Updated reset_db.py (RECOMMENDED)

The script now uses `DROP TABLE ... CASCADE` to handle circular dependencies.

```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python backend/db/tools/reset_db.py reset
```

### Solution 2: Use Nuclear Reset (if Solution 1 fails)

This drops the entire schema and recreates it - guaranteed to work:

```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python backend/db/tools/nuclear_reset.py
```

### Solution 3: Manual SQL (if both fail)

Connect to the database directly:

```bash
# Get a shell in the Docker container
sudo docker compose exec app bash

# Or run psql directly
sudo docker compose exec app psql -U admin -d tdd
```

Then run:
```sql
-- Drop the entire schema
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO admin;
GRANT ALL ON SCHEMA public TO public;
```

Then exit and run:
```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python backend/db/tools/reset_db.py create
```

## What Changed

### reset_db.py
- Now uses `DROP TABLE ... CASCADE` for each table individually
- This drops foreign key constraints along with the tables
- Handles circular dependencies automatically

### nuclear_reset.py (NEW)
- Drops the entire `public` schema
- Recreates the schema with proper permissions
- Creates ENUMs and tables from scratch
- 100% guaranteed to work, no matter how complex the dependencies

## Testing

After reset, verify:
```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python backend/db/tools/verify_schema.py
```

Should output:
```
✅ All required columns are present!
```

## Why This Happened

In your models:
- `ChipStructure` (line 11): `team_id = Column(Integer, ForeignKey("team.id"))`
- `Team` (line 22): `default_chip_structure_id = Column(Integer, ForeignKey("chip_structure.id"))`

This creates a circular reference. It's fine for normal operation, but makes dropping tables tricky.

## Recommendation

**Just use the nuclear reset** - it's simple, fast, and guaranteed to work:

```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python backend/db/tools/nuclear_reset.py
```

This is the cleanest solution when you're recreating from scratch anyway.
