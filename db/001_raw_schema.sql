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

-- page_id is stable; titles are not (never key on title).
CREATE TABLE IF NOT EXISTS raw.page (
    page_id bigint PRIMARY KEY,
    ns integer NOT NULL,
    title text NOT NULL, -- title at dump time
    is_redirect boolean NOT NULL DEFAULT false,
    redirect_target text,
    ingest_run_id bigint REFERENCES raw.ingest_run (id)
);

CREATE INDEX IF NOT EXISTS page_title_idx ON raw.page (title);

CREATE INDEX IF NOT EXISTS page_ns_idx ON raw.page (ns);