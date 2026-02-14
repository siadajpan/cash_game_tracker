# Migration from Host PostgreSQL to Docker Container

## Important: Understanding Your Setup

Your setup:
- **Source**: PostgreSQL running **directly on Raspberry Pi** at `localhost:5432/tdd`
- **Target**: PostgreSQL in Docker container `cashgame_db` at port `5434` (mapped)
- **no_pain_db**: Completely separate container (unrelated to this migration)

## Running the Migration on Raspberry Pi

### Step 1: Enable Host Access from Docker

On Linux (Raspberry Pi), Docker containers need special configuration to access the host's PostgreSQL. Add this to your docker-compose command:

```bash
sudo docker compose run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e PYTHONPATH=. \
  app poetry run python scripts/migrate_database.py --dry-run
```

The `--add-host=host.docker.internal:host-gateway` flag allows the container to reach the host's PostgreSQL.

### Step 2: Ensure Host PostgreSQL Accepts Connections

Your host PostgreSQL must accept connections from Docker containers. Check:

```bash
# Find PostgreSQL config
sudo find /etc -name "postgresql.conf" 2>/dev/null

# Edit the config
sudo nano /etc/postgresql/*/main/postgresql.conf

# Make sure this line is present (or set to '*'):
listen_addresses = '*'

# Also check pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add this line to allow Docker network:
host    all             all             172.17.0.0/16           md5
```

Then restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### Step 3: Run the Migration

**Dry run first:**

```bash
sudo docker compose run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e PYTHONPATH=. \
  app poetry run python scripts/migrate_database.py --dry-run
```

**Actual migration:**

```bash
sudo docker compose run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e PYTHONPATH=. \
  app poetry run python scripts/migrate_database.py
```

## Alternative: Run Directly on Raspberry Pi

If the Docker approach is complex, you can run the script directly on the Raspberry Pi (outside Docker):

```bash
# Install Python dependencies on the host
pip3 install python-dotenv sqlalchemy psycopg2-binary

# Run the migration
python3 scripts/migrate_database.py --dry-run
python3 scripts/migrate_database.py
```

When running on the host, it connects to:
- Source: `localhost:5432/tdd` (host PostgreSQL)
- Target: `localhost:5434/cashgame_tracker` (Docker container via port mapping)

## Verification

After migration, verify both databases:

```bash
# Check source (host PostgreSQL)
psql -h localhost -p 5432 -U admin -d tdd -c "SELECT COUNT(*) FROM users;"

# Check target (Docker container)
sudo docker exec -it cashgame_db psql -U admin -d cashgame_tracker -c "SELECT COUNT(*) FROM users;"
```

The counts should match!

## Diagram

```
┌─────────────────────────────────────────────┐
│           Raspberry Pi (Host)               │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │ PostgreSQL (port 5432)               │  │
│  │ Database: tdd                        │  │
│  │ ← SOURCE (your original data)        │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │ Docker Containers                    │  │
│  │                                      │  │
│  │  ┌────────────────────────────────┐ │  │
│  │  │ cashgame_db (port 5434→5432)   │ │  │
│  │  │ Database: cashgame_tracker     │ │  │
│  │  │ ← TARGET (new isolated DB)     │ │  │
│  │  └────────────────────────────────┘ │  │
│  │                                      │  │
│  │  ┌────────────────────────────────┐ │  │
│  │  │ no_pain_db (port 5433→5432)    │ │  │
│  │  │ Database: no_pain_db           │ │  │
│  │  │ (unrelated, separate app)      │ │  │
│  │  └────────────────────────────────┘ │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Troubleshooting

### "Connection refused" to host.docker.internal

Try finding the host gateway IP manually:

```bash
# Get Docker gateway IP
ip addr show docker0

# Or use this in the docker run command instead:
--add-host=host.docker.internal:172.17.0.1
```

### PostgreSQL Authentication Failed

Make sure the credentials match in:
1. Your host PostgreSQL
2. Your `.env` file
3. Both should use the same `POSTGRES_USER` and `POSTGRES_PASSWORD`

### Alternative: Use Host Network Mode

If `host.docker.internal` doesn't work, use host network mode:

```bash
sudo docker compose run --rm \
  --network=host \
  -e PYTHONPATH=. \
  app poetry run python scripts/migrate_database.py
```

With `--network=host`, the container uses the host's network, so `localhost:5432` directly accesses the host's PostgreSQL.
