-- Add missing columns to multiple tables
-- This script fixes database schema inconsistencies

-- First, create the ENUM types if they don't exist
DO $$ BEGIN
    CREATE TYPE playerrequeststatus AS ENUM ('REQUESTED', 'APPROVED', 'DECLINED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE teamrole AS ENUM ('MEMBER', 'ADMIN');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add columns to user_team_association table
ALTER TABLE user_team_association 
ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';

ALTER TABLE user_team_association 
ADD COLUMN IF NOT EXISTS role teamrole NOT NULL DEFAULT 'MEMBER';

-- Add status column to add_on table
ALTER TABLE add_on 
ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';

-- Add status column to cash_out table
ALTER TABLE cash_out 
ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';

-- Add status column to user_game_association table
ALTER TABLE user_game_association 
ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';

