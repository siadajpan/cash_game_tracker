set shell := ["powershell", "-Command"]

# Target: update
# Fetches and merges the latest changes from the remote repository.
pull:
	@echo "--- Fetching latest code from Git ---"
	git pull

# Target: stop
# Stops and removes all containers, networks, and volumes defined in docker-compose.yml.
# We use 'sudo' here as requested, which is necessary if the user isn't in the docker group.
stop:
	@echo "--- Stopping and removing Docker containers (sudo) ---"
	sudo docker-compose down

start:
	@echo "--- Starting Docker containers (sudo) ---"
	sudo docker-compose up -d

reset_db:
	@echo "--- Resetting database ---"
	poetry run python backend/db/tools/nuclear_reset.py

# Initialize local SQLite database (run this first time)
init_local_db:
	@echo "--- Initializing local SQLite database ---"
	$env:USE_SQLITE="true"; poetry run python backend/db/tools/reset_db.py create

# Start local development server with SQLite (no Docker required)
start_local:
	@echo "--- Starting local server with SQLite ---"
	@echo "Note: If database doesn't exist, run 'just init_local_db' first"
	$env:USE_SQLITE="true"; poetry run uvicorn --host 0.0.0.0 --port 8000 main:app --reload

# Start production fix for sequences (Must be run on the production server)
fix_sequences:
	@echo "--- Fixing Database Sequences (Production) ---"
	sudo docker-compose exec app poetry run python backend/scripts/fix_sequences.py


# Default target runs both
update: pull stop start