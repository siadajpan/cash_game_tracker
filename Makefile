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
	sudo docker-compose down

start:
	@echo "--- Starting Docker containers (sudo) ---"
	sudo docker-compose up -d

reset_db:
	@echo "--- Resetting database ---"
	poetry run python backend/db/tools/reset_db.py

# Default target runs both
update: pull stop start