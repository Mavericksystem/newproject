CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.build_run (
    id bigserial PRIMARY KEY,
    page_id bigint NOT NULL REFERENCES raw.page (page_id),
    parser_version text NOT NULL,
    chunker_version text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running' CHECK (
        status IN ('running', 'done', 'failed')
    ),
    revisions_processed integer NOT NULL DEFAULT 0,
    lineages_created integer NOT NULL DEFAULT 0,
    versions_created integer NOT NULL DEFAULT 0,
    error text
);