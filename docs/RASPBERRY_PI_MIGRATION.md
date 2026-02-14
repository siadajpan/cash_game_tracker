# Running Migration on Raspberry Pi

Since both databases are running in Docker on your Raspberry Pi, you have two options for running the migration:

## Option 1: Run Inside Docker (Recommended ✅)

This is the easiest since the script will automatically detect it's in Docker and connect to both database containers:

```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python scripts/migrate_database.py --dry-run
```

After verifying with dry-run, run the actual migration:

```bash
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python scripts/migrate_database.py
```

**What this does:**
- Runs the migration script inside a temporary container
- The script detects it's running in Docker
- Connects to `no_pain_db` container (source)
- Connects to `cashgame_db` container (target)
- Uses Docker network for communication

## Option 2: Run on Host (If Python is installed)

If you have Python and psycopg2 installed on your Raspberry Pi:

```bash
# Install dependencies first
pip install python-dotenv sqlalchemy psycopg2-binary

# Run migration
python scripts/migrate_database.py --dry-run
python scripts/migrate_database.py
```

## What Changed in the Migration Script

The script now:
1. ✅ **Detects if running inside Docker** (checks for `/.dockerenv`)
2. ✅ **Adjusts connection parameters automatically**:
   - Inside Docker: connects to `no_pain_db:5432` and `cashgame_db:5432`
   - Outside Docker: connects to `localhost:5433` and `localhost:5434`
3. ✅ **Works in both environments** without manual configuration

## Troubleshooting

### Error: "Connection refused"

This means the databases aren't reachable. Check:

```bash
# Verify both databases are running
sudo docker ps

# You should see:
# - no_pain_db (port 5433)
# - cashgame_db (port 5434)
```

### Error: "No such container"

Make sure you're running from the correct directory:

```bash
cd /path/to/cash_game_tracker
sudo docker compose run --rm -e PYTHONPATH=. app poetry run python scripts/migrate_database.py --dry-run
```

### Network Issues

Both database containers must be on the same Docker network. Check:

```bash
sudo docker network ls
sudo docker network inspect cash_game_tracker_default
```

## After Migration

Once migration is complete:

1. **Test the application**:
   ```bash
   sudo docker compose up -d
   # Visit http://localhost:80
   ```

2. **Verify data**:
   ```bash
   # Connect to new database
   sudo docker exec -it cashgame_db psql -U admin -d cashgame_tracker
   
   # Check tables
   \dt
   
   # Check some data
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM games;
   \q
   ```

3. **Your no_pain app** continues running unaffected on port 8001

## Quick Reference

| Command | Purpose |
|---------|---------|
| `sudo docker compose up -d db` | Start just the database |
| `sudo docker compose up -d` | Start everything |
| `sudo docker compose ps` | Check status |
| `sudo docker compose logs db` | View database logs |
| `sudo docker exec -it cashgame_db psql -U admin -d cashgame_tracker` | Connect to database |

## Environment Variables

The migration script uses `.env` settings automatically. The key variables are:

```bash
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=cashgame_tracker
```

These are used by both the migration script and Docker containers.
