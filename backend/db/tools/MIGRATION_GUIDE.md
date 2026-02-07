# Database Schema Migration Guide

## Problem
Your database schema is out of sync with the SQLAlchemy models. Several tables are missing columns:
- `user_team_association`: missing `status` and `role` columns
- `add_on`: missing `status` column
- `cash_out`: missing `status` column
- `user_game_association`: missing `status` column

## Solution

### Option 1: Run the Migration Script (RECOMMENDED - Safe, No Data Loss)

This will add the missing columns to your existing database without losing any data.

**On your local Windows machine:**
```powershell
poetry run python backend\db\tools\add_missing_columns.py
```

**On your Linux server (in SSH):**
```bash
poetry run python backend/db/tools/add_missing_columns.py
```

### Option 2: Use SQL Directly

If you have direct PostgreSQL access, you can run the SQL script:

```bash
# With psql
psql -U admin -d tdd -h localhost -p 5432 -f backend/db/tools/add_missing_columns.sql

# Or connect and paste the SQL
psql -U admin -d tdd -h localhost -p 5432
# Then paste the contents of add_missing_columns.sql
```

### Option 3: Reset Database (DANGEROUS - Will Delete All Data)

**⚠️ WARNING: This will DELETE ALL DATA in your database!**

Only use this for a fresh start:

```bash
poetry run python backend/db/tools/reset_db.py reset
```

## Verification

After running the migration, verify that all columns were added successfully:

```bash
poetry run python backend/db/tools/verify_schema.py
```

## Files Created/Updated

1. **backend/db/tools/add_missing_columns.py** - Python migration script (RECOMMENDED)
2. **backend/db/tools/add_missing_columns.sql** - SQL migration script (alternative)
3. **backend/db/tools/verify_schema.py** - Verification script
4. **backend/db/tools/reset_db.py** - Updated to properly create ENUMs before tables

## Root Cause

The issue occurred because:
1. The database was created without the ENUM types being created first
2. Tables that depend on ENUM columns couldn't create those columns properly
3. The schema drifted from the models over time

## Prevention

The `reset_db.py` script has been updated to create ENUM types before creating tables, preventing this issue in the future.

## Next Steps

1. **Run the migration** on your server (where the database actually is)
2. **Verify** the schema with the verification script
3. **Test** your application to ensure everything works
4. **Commit** these migration scripts to your repository

## Troubleshooting

### Can't connect to database
- Check your `.env` file has the correct database credentials
- Ensure the PostgreSQL server is running
- Verify you're running the script on the correct machine (where the DB is accessible)

### Permission denied
- Make sure your database user has ALTER TABLE permissions
- Try running with a superuser account if needed

### Script already ran but still getting errors
- Clear your application cache/restart the server
- Check if ENUMs were created: `\dT+ playerrequeststatus` in psql
- Verify columns exist: `\d+ user_team_association` in psql
