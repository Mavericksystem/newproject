CREATE EXTENSION IF NOT EXISTS vector;
-- not used until Phase 3, ready for it

CREATE SCHEMA IF NOT EXISTS raw;

-- One row per loader execution: provenance for everything loaded.
CREATE TABLE IF NOT EXISTS raw.ingest_run (
    id bigserial PRIMARY KEY,
    source_file text NOT NULL,
    loader_version text NOT NULL,
    selection text NOT NULL, -- what was asked for (titles / all-articles)
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running' CHECK (
        status IN ('running', 'done', 'failed')
    ),
    pages_loaded integer NOT NULL DEFAULT 0,
    revisions_loaded integer NOT NULL DEFAULT 0,
    error text
);