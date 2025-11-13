# Running locally
## Database
Install PostgreSQL and create a user and password

## Update .env file
1. Update the values in the .env_template and 
2. Rename the file to .env

## Running
```shell
cd backend
poetry run uvicorn backend.main:app --reload
```
To view the page, open
```shell
localhost:8000
```
## Tests
To run tests:
```shell
poetry run pytest backend/tests
```
# Using Docker
```shell
docker-compose --env-file .env up --build
```