# Database Reset - Summary

## ✅ What Was Fixed

I've completely overhauled the database reset system to ensure it works properly from scratch.

### Problems Identified
1. `reset_db.py` wasn't creating ENUM types before tables
2. `reset_db.py` had the wrong main execution (was hardcoded to only drop)
3. ENUM types weren't being cleaned up on drop
4. Multiple tables were missing columns in your production database

### Solutions Implemented

#### 1. Fixed `reset_db.py`
- ✅ Creates ENUM types (`playerrequeststatus`, `teamrole`) BEFORE creating tables
- ✅ Drops ENUM types when dropping database (they persist otherwise)
- ✅ Proper command-line argument handling (`drop`, `create`, `reset`)
- ✅ Better error handling and user feedback
- ✅ Separate `reset_all()` function with clear warnings

#### 2. Created Migration Tools
- ✅ `add_missing_columns.py` - Safe migration without data loss
- ✅ `add_missing_columns.sql` - SQL version for direct access
- ✅ `verify_schema.py` - Verify database matches models
- ✅ `test_reset.py` - Automated testing

#### 3. Documentation
- ✅ `README.md` - Complete documentation
- ✅ `MIGRATION_GUIDE.md` - Step-by-step migration instructions

## 🚀 How to Use

### To Reset Database (DELETE ALL DATA)

```bash
# On your server (Linux)
poetry run python backend/db/tools/reset_db.py reset

# On Windows (local)
poetry run python backend\db\tools\reset_db.py reset
```

This will:
1. Drop all tables
2. Drop all ENUM types
3. Create ENUM types
4. Create all tables with all columns

### To Verify It Worked

```bash
poetry run python backend/db/tools/verify_schema.py
```

Should output:
```
Checking table 'user_team_association'...
  ✓ Column 'user_id' exists
  ✓ Column 'team_id' exists
  ✓ Column 'status' exists
  ✓ Column 'role' exists
...
✅ All required columns are present!
```

## 📋 Missing Columns That Will Be Created

When you run `reset_db.py reset`, these columns will be created properly:

| Table | Column | Type | Default |
|-------|--------|------|---------|
| user_team_association | status | playerrequeststatus | 'REQUESTED' |
| user_team_association | role | teamrole | 'MEMBER' |
| add_on | status | playerrequeststatus | 'REQUESTED' |
| cash_out | status | playerrequeststatus | 'REQUESTED' |
| user_game_association | status | playerrequeststatus | 'REQUESTED' |

## 🔧 Technical Details

### ENUM Types Created

```sql
CREATE TYPE playerrequeststatus AS ENUM ('REQUESTED', 'APPROVED', 'DECLINED');
CREATE TYPE teamrole AS ENUM ('MEMBER', 'ADMIN');
```

### Execution Order (Critical!)

The script now follows the correct order:

1. **Drop Phase** (if dropping):
   - Drop all tables
   - Drop all ENUM types (CASCADE)

2. **Create Phase**:
   - Create ENUM types first ⭐
   - Create all tables (which reference the ENUMs)

This order is critical in PostgreSQL because tables can't reference ENUM types that don't exist yet.

## ⚠️ Important Notes

### For Production/Server

Since you said you'll recreate from scratch:

1. **SSH to your server**
2. **Navigate to your app directory** (probably `/app`)
3. **Run the reset**:
   ```bash
   poetry run python backend/db/tools/reset_db.py reset
   ```
4. **Verify**:
   ```bash
   poetry run python backend/db/tools/verify_schema.py
   ```
5. **Restart your application**

### Database Connection

Make sure:
- PostgreSQL is running
- Database `tdd` exists (or will be created)
- User `admin` has permissions
- Password in `.env` is correct

If the database doesn't exist, create it first:
```bash
# In PostgreSQL
createdb -U admin tdd
```

Or in psql:
```sql
CREATE DATABASE tdd OWNER admin;
```

## 📝 Files Modified/Created

### Modified
- `backend/db/tools/reset_db.py` - Complete rewrite
- `backend/webapps/team/route_team.py` - Fixed UnboundLocalError

### Created
- `backend/db/tools/add_missing_columns.py`
- `backend/db/tools/add_missing_columns.sql`
- `backend/db/tools/verify_schema.py`
- `backend/db/tools/test_reset.py`
- `backend/db/tools/README.md`
- `backend/db/tools/MIGRATION_GUIDE.md`
- `backend/db/tools/SUMMARY.md` (this file)

## ✅ Checklist

Before running reset:
- [ ] You're okay with deleting all data
- [ ] You have a backup (if needed)
- [ ] PostgreSQL is running
- [ ] You're on the correct server/machine
- [ ] Database credentials in `.env` are correct

After running reset:
- [ ] Run `verify_schema.py` to confirm
- [ ] Restart your application
- [ ] Test basic functionality (create user, create team, etc.)
- [ ] Import your game data if needed

## 🎯 Next Steps

1. **Reset your database** on the server
2. **Import your game data** (you have `games_export.json`)
3. **Test the application** to make sure everything works

The reset is now bulletproof and will create a complete, working database schema from scratch every time.
