# Database Separation - Summary of Changes

## Overview

Your cash game tracker now has its own dedicated PostgreSQL database running in a Docker container, completely separate from your "no_pain" app's database.

## What Changed

### 1. Docker Compose Configuration
**File**: `docker-compose.yml`
- **Added**: PostgreSQL 15 Alpine service (`db`)
  - Container name: `cashgame_db`
  - Port mapping: `5434:5432` (avoids conflict with port 5433)
  - Health checks enabled
  - Persistent volume: `cashgame_postgres_data`
- **Updated**: App service now depends on healthy database

### 2. Environment Configuration

#### `.env` (for local development)
- **Changed**: `POSTGRES_PORT` from `5433` → `5434`
- **Changed**: `POSTGRES_DB` from `tdd` → `cashgame_tracker`
- **Added**: Comments explaining local vs Docker configuration

#### `.env.docker` (new file for Docker deployment)
- **Purpose**: Used when running the app in Docker
- **Key difference**: `POSTGRES_SERVER=db` (Docker service name)
- **Note**: This file is auto-loaded by docker-compose

#### `.env.docker.template` (new template file)
- **Purpose**: Template for creating `.env.docker`
- **Safe to commit**: Contains placeholder values

### 3. Migration Tools

#### `scripts/migrate_database.py` (new)
- **Purpose**: Migrate data from old database to new one
- **Features**:
  - Dry-run mode
  - Automatic verification
  - Two migration methods (pg_dump + SQLAlchemy fallback)
  - Detailed progress reporting

#### `scripts/setup_database.py` (new)
- **Purpose**: Quick interactive setup
- **Features**:
  - Checks Docker status
  - Creates `.env.docker`
  - Starts database container
  - Optionally runs migration

### 4. Documentation

#### `docs/DATABASE_MIGRATION.md` (new)
- Complete migration guide
- Troubleshooting tips
- Backup/restore procedures
- Instructions for moving to different hardware

## Old vs New Setup

### Before
```
┌─────────────────────────────────────────┐
│  PostgreSQL (localhost:5433)            │
│  ┌────────────────┐  ┌────────────────┐ │
│  │   Database:    │  │   Database:    │ │
│  │      tdd       │  │   no_pain_db   │ │
│  │ (cash tracker) │  │  (no_pain app) │ │
│  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────┘
```

### After
```
┌──────────────────────────────┐  ┌────────────────────────────────┐
│ PostgreSQL (localhost:5433)  │  │ PostgreSQL (localhost:5434)    │
│  ┌────────────────────────┐  │  │  ┌──────────────────────────┐  │
│  │    Database:           │  │  │  │     Database:            │  │
│  │    no_pain_db          │  │  │  │  cashgame_tracker        │  │
│  │   (no_pain app)        │  │  │  │  (cash tracker)          │  │
│  └────────────────────────┘  │  │  └──────────────────────────┘  │
└──────────────────────────────┘  └────────────────────────────────┘
     No changes                       New Docker container
```

## Quick Start

### Option 1: Automated Setup (Recommended)
```bash
python scripts/setup_database.py
```

### Option 2: Manual Setup
```bash
# 1. Start the database
docker-compose up -d db

# 2. Migrate data (dry-run first)
python scripts/migrate_database.py --dry-run

# 3. Migrate data (actual)
python scripts/migrate_database.py

# 4. Test locally
just start_local
```

### Option 3: Full Docker Deployment
```bash
# Copy and configure .env.docker
cp .env.docker.template .env.docker
# Edit .env.docker with your credentials

# Start everything
docker-compose up -d

# Access at http://localhost:80
```

## Configuration Reference

### Local Development
- **Database**: `localhost:5434`
- **Env file**: `.env`
- **Server setting**: `POSTGRES_SERVER=localhost`

### Docker Deployment
- **Database**: `db:5432` (internal Docker network)
- **Env file**: `.env.docker`
- **Server setting**: `POSTGRES_SERVER=db`

## Port Allocation

- **5433**: PostgreSQL for "no_pain" app (unchanged)
- **5434**: PostgreSQL for cash game tracker (new)
- **8000**: FastAPI app (local development)
- **80**: FastAPI app (Docker deployment)
- **8001**: No_pain app

## Benefits

1. **Isolation**: Each app has its own database
2. **No conflicts**: Different ports for each database
3. **Easy migration**: Docker volume makes hardware migration simple
4. **Security**: Separate credentials for each app
5. **Maintenance**: Can update/restart independently

## Important Notes

- Both databases run independently
- The "no_pain" app is **not affected** by these changes
- You can still access the old database on port 5433
- The new database is on port 5434
- Don't delete old database until you've verified everything works!

## Troubleshooting

See `docs/DATABASE_MIGRATION.md` for detailed troubleshooting steps.

Common issues:
- **Port conflict**: Change port in docker-compose.yml
- **Connection failed**: Check Docker is running
- **Migration failed**: Use SQLAlchemy method with `--use-sqlalchemy` flag

## Files Modified

- ✏️ `docker-compose.yml` - Added database service
- ✏️ `.env` - Updated port and database name
- ➕ `.env.docker` - Docker-specific configuration
- ➕ `.env.docker.template` - Template for .env.docker
- ➕ `scripts/migrate_database.py` - Migration script
- ➕ `scripts/setup_database.py` - Setup script
- ➕ `docs/DATABASE_MIGRATION.md` - Migration guide
- ➕ `docs/DATABASE_SEPARATION_SUMMARY.md` - This file

## Next Steps

1. ✅ Files have been updated
2. ⏳ Run setup: `python scripts/setup_database.py`
3. ⏳ Verify migration worked correctly
4. ⏳ Test your application
5. ⏳ Deploy to production when ready
