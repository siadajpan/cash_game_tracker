# Database Tools Documentation

This directory contains tools for managing the database schema.

## Quick Start

### Reset Database (Fresh Start)

**⚠️ WARNING: This DELETES ALL DATA!**

```bash
# On Windows
poetry run python backend\db\tools\reset_db.py reset

# On Linux/Mac
poetry run python backend/db/tools/reset_db.py reset
```

### Add Missing Columns (Safe Migration)

If you have existing data and just need to add missing columns:

```bash
poetry run python backend/db/tools/add_missing_columns.py
```

### Verify Schema

Check if your database schema matches the models:

```bash
poetry run python backend/db/tools/verify_schema.py
```

## Available Scripts

### `reset_db.py`

Complete database management script.

**Usage:**
```bash
python backend/db/tools/reset_db.py [command]
```

**Commands:**
- `drop` - Drop all tables and ENUM types
- `create` - Create ENUM types and all tables
- `reset` - Drop everything and recreate (DELETES ALL DATA)

**What it does:**
1. Drops all tables (if command is `drop` or `reset`)
2. Drops all ENUM types (PostgreSQL custom types)
3. Creates ENUM types (`playerrequeststatus`, `teamrole`)
4. Creates all tables with proper foreign keys and constraints

**Important:** This script properly creates ENUM types BEFORE creating tables, which is critical for PostgreSQL.

### `add_missing_columns.py`

Safe migration script that adds missing columns without losing data.

**Usage:**
```bash
python backend/db/tools/add_missing_columns.py
```

**What it does:**
- Creates ENUM types if they don't exist
- Adds missing `status` column to: `user_team_association`, `add_on`, `cash_out`, `user_game_association`
- Adds missing `role` column to: `user_team_association`
- All columns are added with `IF NOT EXISTS`, so it's safe to run multiple times

**Use this when:**
- You have existing data you want to keep
- Your schema is out of sync with the models
- You're getting "column does not exist" errors

### `verify_schema.py`

Verification script to check if all required columns exist.

**Usage:**
```bash
python backend/db/tools/verify_schema.py
```

**What it does:**
- Checks if all required tables exist
- Verifies that all required columns exist in each table
- Reports missing columns
- Exit code 0 = all good, 1 = problems found

**Use this to:**
- Verify migrations worked correctly
- Debug schema issues
- Validate database state before deployment

### `test_reset.py`

Automated test script for the reset workflow.

**Usage:**
```bash
python backend/db/tools/test_reset.py
```

**What it does:**
- Runs a full database reset
- Verifies the schema is correct
- Reports success/failure

### `add_missing_columns.sql`

SQL version of the migration script for direct database access.

**Usage:**
```bash
psql -U [username] -d [database] -f backend/db/tools/add_missing_columns.sql
```

## Common Workflows

### First Time Setup

```bash
# 1. Reset database
poetry run python backend/db/tools/reset_db.py reset

# 2. Verify it worked
poetry run python backend/db/tools/verify_schema.py
```

### After Pulling New Code

If the schema changed:

```bash
# Option 1: Safe migration (keeps data)
poetry run python backend/db/tools/add_missing_columns.py
poetry run python backend/db/tools/verify_schema.py

# Option 2: Fresh start (loses data)
poetry run python backend/db/tools/reset_db.py reset
```

### Fixing "Column Does Not Exist" Errors

```bash
# 1. Try safe migration first
poetry run python backend/db/tools/add_missing_columns.py

# 2. If that doesn't work, check what's missing
poetry run python backend/db/tools/verify_schema.py

# 3. If you can lose data, reset
poetry run python backend/db/tools/reset_db.py reset
```

### Deployment to Production

**Never run reset in production!** Use migrations instead:

```bash
# SSH to production server
ssh your-server

# Navigate to app directory
cd /app

# Run safe migration
poetry run python backend/db/tools/add_missing_columns.py

# Verify
poetry run python backend/db/tools/verify_schema.py

# Restart application
# (method depends on your deployment)
```

## Database Schema Details

### ENUM Types

The database uses PostgreSQL ENUM types:

1. **`playerrequeststatus`**
   - Values: `REQUESTED`, `APPROVED`, `DECLINED`
   - Used in: `user_team_association`, `add_on`, `cash_out`, `user_game_association`

2. **`teamrole`**
   - Values: `MEMBER`, `ADMIN`
   - Used in: `user_team_association`

### Tables Managed

All tables defined in `backend/db/models/`:
- `user` - User accounts
- `team` - Teams/groups
- `game` - Poker games
- `user_team_association` - User-team relationships
- `user_game_association` - User-game relationships
- `buy_in` - Buy-in records
- `add_on` - Add-on records
- `cash_out` - Cash-out records
- `chip_structure` - Chip structures
- `chip` - Chip definitions
- `chip_amount` - Chip amounts
- `user_verification` - Email verification tokens

## Troubleshooting

### "Type already exists" error

This is usually harmless. The scripts use `checkfirst=True` and `IF NOT EXISTS` to avoid this.

### "Permission denied" error

Your database user needs these permissions:
- CREATE TYPE
- CREATE TABLE
- ALTER TABLE
- DROP TABLE
- DROP TYPE

### "Cannot connect to database" error

Check:
1. PostgreSQL is running
2. Credentials in `.env` are correct
3. Database exists
4. Network/firewall allows connection

### Reset doesn't work

Try manual cleanup:

```sql
-- Connect to database
psql -U [username] -d [database]

-- Drop everything manually
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO [username];
GRANT ALL ON SCHEMA public TO public;
```

Then run `reset_db.py reset`.

## Development Notes

### Adding New Models

When you add a new model:

1. Create the model file in `backend/db/models/`
2. Import it in `backend/db/base.py`
3. Run `reset_db.py reset` in development
4. Create a migration script for production (like `add_missing_columns.py`)

### Adding New ENUM Types

1. Create the ENUM definition (like `player_request_status.py`)
2. Import it in `reset_db.py`
3. Add it to the `create_all()` function
4. Add drop statement in `drop_all()` function

### Schema Changes

For production:
1. Never use `reset_db.py` (it deletes data!)
2. Create migration scripts that add/modify without deleting
3. Test migrations on a copy of production data first
4. Always have a backup before running migrations

## File Structure

```
backend/db/tools/
├── README.md                    # This file
├── reset_db.py                  # Main database reset tool
├── add_missing_columns.py       # Safe migration script
├── add_missing_columns.sql      # SQL version of migration
├── verify_schema.py             # Schema verification
├── test_reset.py                # Automated tests
└── MIGRATION_GUIDE.md          # Detailed migration guide
```
