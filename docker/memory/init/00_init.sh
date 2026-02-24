#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- memu-py will also run CREATE EXTENSION in ddl_mode='create',
    -- but running here first ensures it's available before memu-py connects
    CREATE EXTENSION IF NOT EXISTS vector;
    ALTER SYSTEM SET maintenance_work_mem = '128MB';
    ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
    SELECT pg_reload_conf();
EOSQL
