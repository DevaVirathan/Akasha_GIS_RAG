-- Runs automatically on FIRST postgres start (empty data volume), against
-- POSTGRES_DB. Enables the extensions the schema in Plan/03 depends on.
-- To re-run after schema changes, recreate the volume: docker compose down -v.

CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector: VECTOR type + ANN indexes
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;    -- case-insensitive, unique emails
