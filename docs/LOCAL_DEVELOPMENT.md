# Local Development with SQLite

## Overview

Your local development now uses **SQLite** instead of PostgreSQL, which means:
- ✅ No Docker required for local testing
- ✅ Faster startup
- ✅ Simpler setup
- ✅ Database stored in `sql_app.db` file

## Quick Start

### First Time Setup

```bash
# 1. Initialize the SQLite database
just init_local_db

# 2. Start the local server
just start_local
```

### Daily Development

```bash
# Just run this to start developing
just start_local
```

Visit `http://localhost:8000` 🚀

## How It Works

The application checks the `USE_SQLITE` environment variable:

- **`USE_SQLITE=true`** → Uses SQLite (`sql_app.db`)
- **`USE_SQLITE=false` or not set** → Uses PostgreSQL (requires Docker)

### Local Development (justfile)
```bash
just start_local  # Automatically sets USE_SQLITE=true
```

### Docker/Production
```bash
docker-compose up  # Uses PostgreSQL in Docker
```

## Database Commands

### Initialize/Create Database
```bash
just init_local_db
```

### Reset Database (Delete All Data)
```bash
# Set USE_SQLITE environment variable, then reset
$env:USE_SQLITE="true"
poetry run python backend/db/tools/reset_db.py reset
```

### Check Database
```bash
# View tables in SQLite
sqlite3 sql_app.db ".tables"

# Or use a SQLite browser
# Download: https://sqlitebrowser.org/
```

## Database Files

- **`sql_app.db`** - Your local SQLite database
  - ✅ Added to `.gitignore` (won't be committed)
  - ⚠️ Only for local development
  - 🗑️ Safe to delete and recreate anytime

## Switching Between Databases

### Use SQLite (Local)
```bash
$env:USE_SQLITE="true"
poetry run uvicorn main:app
```

### Use PostgreSQL (Docker)
```bash
# Start Docker database first
docker-compose up -d db

# Then run app (USE_SQLITE not set or false)
poetry run uvicorn main:app
```

## Production Deployment

**Production always uses PostgreSQL in Docker:**

```bash
docker-compose up -d
# Automatically uses PostgreSQL (USE_SQLITE is not set)
```

## Troubleshooting

### "Database not ready" error
This means it's trying to connect to PostgreSQL. Make sure:
```bash
# Check that USE_SQLITE is set
just start_local  # This sets it automatically
```

### Database file corrupted
Simply recreate it:
```bash
rm sql_app.db
just init_local_db
```

### Need to test with PostgreSQL locally
```bash
# Start Docker database
docker-compose up -d db

# Run without USE_SQLITE
poetry run uvicorn main:app
```

## Best Practices

1. **Use SQLite for**:
   - ✅ Local development
   - ✅ Quick testing
   - ✅ Running without Docker

2. **Use PostgreSQL for**:
   - ✅ Production deployment
   - ✅ Testing production-specific features
   - ✅ Testing with real data volumes

3. **Remember**:
   - SQLite database is local only (not shared)
   - Don't commit `sql_app.db` to Git
   - Production always uses PostgreSQL

## Summary

```
┌─────────────────────────────────────────┐
│  Local Development (Windows)            │
│                                         │
│  Command: just start_local              │
│  Database: SQLite (sql_app.db)          │
│  Port: 8000                             │
│  Docker: Not required ✅                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Production (Docker/Raspberry Pi)       │
│                                         │
│  Command: docker-compose up -d          │
│  Database: PostgreSQL (cashgame_db)     │
│  Port: 80 or 8000                       │
│  Docker: Required ✅                    │
└─────────────────────────────────────────┘
```

Happy coding! 🎉
