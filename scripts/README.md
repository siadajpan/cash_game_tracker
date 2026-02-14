# Database Management Scripts

This directory contains scripts for managing your cash game tracker database.

## Available Scripts

Currently, there are no standalone scripts in this directory. Database management is handled through the backend tools.

## Database Management

All database operations are available through the backend tools:

### Reset Database

**WARNING: This will delete all data!**

```bash
# Full reset (drop and recreate everything)
poetry run python backend/db/tools/reset_db.py reset

# Drop tables and ENUMs only
poetry run python backend/db/tools/reset_db.py drop

# Create tables and ENUMs only
poetry run python backend/db/tools/reset_db.py create
```

### Verify Schema

Check if all expected tables and columns exist:

```bash
poetry run python backend/db/tools/verify_schema.py
```

### Check Tables

List all tables in the database:

```bash
poetry run python backend/db/tools/check_tables.py
```

## Docker Database Access

If you're using Docker, you can access the database directly:

```bash
# Connect to the database
docker exec -it cashgame_db psql -U admin -d cashgame_tracker

# Run a query
docker exec cashgame_db psql -U admin -d cashgame_tracker -c "SELECT COUNT(*) FROM \"user\";"

# Backup the database
docker exec cashgame_db pg_dump -U admin -d cashgame_tracker > backup.sql

# Restore from backup
cat backup.sql | docker exec -i cashgame_db psql -U admin -d cashgame_tracker
```

## Backup & Restore

### Create Backup

```bash
# Using Docker
docker exec cashgame_db pg_dump -U admin -d cashgame_tracker -F c -f /tmp/backup.dump
docker cp cashgame_db:/tmp/backup.dump ./backup_$(date +%Y%m%d).dump

# Or compress it
docker exec cashgame_db pg_dump -U admin -d cashgame_tracker | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore from Backup

```bash
# From custom format backup
docker cp ./backup.dump cashgame_db:/tmp/backup.dump
docker exec cashgame_db pg_restore -U admin -d cashgame_tracker -c /tmp/backup.dump

# From SQL backup
cat backup.sql | docker exec -i cashgame_db psql -U admin -d cashgame_tracker

# From compressed backup
gunzip -c backup.sql.gz | docker exec -i cashgame_db psql -U admin -d cashgame_tracker
```

## Database Configuration

The database configuration is managed through environment variables:

- **`.env`** - For local development
- **`.env.docker`** - For Docker deployment

Key variables:
```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_SERVER=localhost  # or 'db' in Docker
POSTGRES_PORT=5434        # Docker mapped port
POSTGRES_DB=cashgame_tracker
```

## Troubleshooting

### Can't connect to database

```bash
# Check if database container is running
docker ps | grep cashgame_db

# Check database logs
docker logs cashgame_db

# Restart database
docker-compose restart db
```

### Need to recreate database

```bash
# Stop and remove everything
docker-compose down -v

# Start fresh
docker-compose up -d db

# Initialize schema
poetry run python backend/db/tools/reset_db.py create
```

## Documentation

For more information, see:
- `backend/db/tools/README.md` - Database tools documentation
- `README.md` - Main project documentation
