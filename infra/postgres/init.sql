-- Stagehand Postgres bootstrap
-- The database itself is created by the POSTGRES_DB env var in docker-compose.
-- This file is a placeholder for any extensions or seed bootstrap needed at
-- container init time. Application tables are managed via Alembic migrations
-- (Milestone 1+), not here.

-- Enable UUID generation (used by application tables later).
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
