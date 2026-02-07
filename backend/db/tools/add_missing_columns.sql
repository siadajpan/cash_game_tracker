-- Add missing columns to user_team_association table

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

-- Add the status column
ALTER TABLE user_team_association 
ADD COLUMN IF NOT EXISTS status playerrequeststatus NOT NULL DEFAULT 'REQUESTED';

-- Add the role column
ALTER TABLE user_team_association 
ADD COLUMN IF NOT EXISTS role teamrole NOT NULL DEFAULT 'MEMBER';
