.PHONY: update stop start

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
	sudo docker compose down

start:
	@echo "--- Starting Docker containers (sudo) ---"
	sudo docker compose up -d

build:
	@echo "--- Building Docker containers (sudo) ---"
	sudo docker compose up -d --build

reset_db:
	@echo "--- Resetting database ---"
	poetry run python backend/db/tools/reset_db.py

reset_db_docker:
	@echo "--- Resetting database (docker) ---"
	sudo docker compose run --rm -e PYTHONPATH=. app poetry run python backend/db/tools/nuclear_reset.py

start_local:
	@echo "--- Starting local server ---"
	poetry run uvicorn --host 0.0.0.0 --port 8000 main:app --reload

start_debug:
	@echo "--- Starting debug server ---"
	poetry run uvicorn --host 0.0.0.0 --port 8000 main:app --reload --debug

# Default target runs both
update: pull stop start
rebuild: pull stop build
