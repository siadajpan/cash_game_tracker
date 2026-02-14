-- Create the cashgame_tracker database if it doesn't exist
SELECT 'CREATE DATABASE cashgame_tracker'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cashgame_tracker')\gexec
