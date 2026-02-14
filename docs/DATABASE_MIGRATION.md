# Database Migration Guide

This guide will help you migrate your cash game tracker database from the shared PostgreSQL instance to a new dedicated Docker container.

## Overview

**Old Setup:**
- Shared PostgreSQL on `localhost:5433`
- Database name: `tdd`
- Shared with the "no_pain" app

**New Setup:**
- Dedicated PostgreSQL Docker container on `localhost:5434`
- Database name: `cashgame_tracker`
- Isolated from other applications

## Benefits of Separate Databases

1. **Isolation**: Issues in one app won't affect the other
2. **Security**: Each app has its own credentials
3. **Portability**: Easy to move/backup/restore independently
4. **Version control**: Different apps can use different PostgreSQL versions
5. **Resource management**: Better control over each database's resources

## Migration Steps

### 1. Start the New Database

First, start the new PostgreSQL database container:

```bash
docker-compose up -d db
```

Wait for the database to be healthy:

```bash
docker-compose ps
```

You should see `cashgame_db` with status "healthy".

### 2. Run Migration Script (Dry Run)

Before actually migrating, do a dry run to see what will happen:

```bash
python scripts/migrate_database.py --dry-run
```

This will show you:
- All tables that will be migrated
- Number of rows in each table
- Total data to be transferred

### 3. Perform the Migration

When you're ready, run the actual migration:

```bash
python scripts/migrate_database.py
```

The script will:
1. Connect to both databases
2. Show you what will be migrated
3. Ask for confirmation
4. Dump data from the old database
5. Restore to the new database
6. Verify the migration was successful

**Note**: The script uses `pg_dump` and `psql` if available (recommended), otherwise falls back to SQLAlchemy-based migration.

### 4. Verify the Migration

After migration, check that everything looks correct:

```bash
# Connect to the new database
docker exec -it cashgame_db psql -U admin -d cashgame_tracker

# List all tables
\dt

# Check some sample data
SELECT * FROM users LIMIT 5;
SELECT * FROM games LIMIT 5;

# Exit psql
\q
```

### 5. Test Your Application

Test your application with the new database:

```bash
# If using justfile
just start_local

# Or manually
poetry run uvicorn main:app --reload
```

Access your app at `http://localhost:8000` and verify:
- You can log in
- All your games are visible
- Player stats are correct
- You can create new games

### 6. Deploy with Docker (Optional)

If you want to run the entire application in Docker:

```bash
# Build and start both database and app
docker-compose up -d

# View logs
docker-compose logs -f

# Access the app at http://localhost:80
```

**Important**: The `.env.docker` file is used when running in Docker, which sets `POSTGRES_SERVER=db` (the Docker service name) instead of `localhost`.

## Configuration Files

### For Local Development

Use `.env` (already updated):
```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5434
POSTGRES_DB=cashgame_tracker
```

### For Docker Deployment

Use `.env.docker` (automatically used by docker-compose):
```bash
POSTGRES_SERVER=db  # Docker service name
POSTGRES_PORT=5432  # Internal Docker port
POSTGRES_DB=cashgame_tracker
```

## Troubleshooting

### Migration Script Fails

If the migration script fails:

1. **Check database connections**:
   ```bash
   # Old database
   psql -h localhost -p 5433 -U admin -d tdd
   
   # New database
   docker exec -it cashgame_db psql -U admin -d cashgame_tracker
   ```

2. **Use SQLAlchemy method**:
   ```bash
   python scripts/migrate_database.py --use-sqlalchemy
   ```

3. **Manual migration**:
   ```bash
   # Dump old database
   pg_dump -h localhost -p 5433 -U admin -d tdd -F p -f backup.sql
   
   # Restore to new database
   docker exec -i cashgame_db psql -U admin -d cashgame_tracker < backup.sql
   ```

### App Can't Connect to Database

1. **Check Docker is running**:
   ```bash
   docker-compose ps
   ```

2. **Check database is healthy**:
   ```bash
   docker-compose logs db
   ```

3. **Verify .env settings**:
   - For local dev: `POSTGRES_SERVER=localhost`, `POSTGRES_PORT=5434`
   - For Docker: Use `.env.docker` with `POSTGRES_SERVER=db`

### Port Conflicts

If port 5434 is already in use, you can change it:

1. Edit `docker-compose.yml`:
   ```yaml
   ports:
     - "5435:5432"  # Use 5435 instead
   ```

2. Update `.env`:
   ```bash
   POSTGRES_PORT=5435
   ```

## Database Backup & Restore

### Backup

```bash
# Create backup
docker exec cashgame_db pg_dump -U admin -d cashgame_tracker -F c -f /tmp/backup.dump

# Copy backup out of container
docker cp cashgame_db:/tmp/backup.dump ./backup_$(date +%Y%m%d).dump
```

### Restore

```bash
# Copy backup into container
docker cp ./backup_20260214.dump cashgame_db:/tmp/backup.dump

# Restore
docker exec cashgame_db pg_restore -U admin -d cashgame_tracker -c /tmp/backup.dump
```

## Moving to Different Hardware

Since your database is now in Docker, moving to different hardware is simple:

1. **Backup the Docker volume**:
   ```bash
   docker run --rm -v cash_game_tracker_cashgame_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/db_backup.tar.gz -C /data .
   ```

2. **Transfer to new hardware**:
   ```bash
   scp db_backup.tar.gz user@new-host:/path/to/cash_game_tracker/
   ```

3. **Restore on new hardware**:
   ```bash
   # On new hardware
   docker-compose up -d db
   docker run --rm -v cash_game_tracker_cashgame_postgres_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/db_backup.tar.gz"
   docker-compose restart db
   ```

## Cleanup Old Database (After Verification)

Once you've verified everything works with the new database, you can stop using the old one:

1. Your "no_pain" app is still using `localhost:5433` (unaffected)
2. Your cash game tracker is now using `localhost:5434` (new database)
3. Both apps are now properly isolated

**Do not delete the old database** until you're 100% confident the migration was successful and you've tested everything thoroughly!

## Questions?

If you encounter any issues:
1. Check the logs: `docker-compose logs db`
2. Verify connections: `docker exec -it cashgame_db psql -U admin -d cashgame_tracker`
3. Review this guide's troubleshooting section
