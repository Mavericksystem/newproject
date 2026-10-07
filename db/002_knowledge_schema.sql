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

CREATE TABLE IF NOT EXISTS knowledge.chunk_lineage (
    id bigserial PRIMARY KEY,
    page_id bigint NOT NULL REFERENCES raw.page (page_id),
    first_rev_id bigint NOT NULL REFERENCES raw.revision (rev_id),  -- revision where it first appeared
    -- How the lineage began. 'split' and 'merged' are marked explicitly, never forced 1:1.
    origin text NOT NULL DEFAULT 'new' CHECK (origin IN ('new', 'split', 'merged')),
    related_lineage_ids bigint[],  -- lineages it was split from / merged from (informational)
    build_run_id bigint NOT NULL REFERENCES knowledge.build_run (id)
);

CREATE INDEX IF NOT EXISTS chunk_lineage_page_idx ON knowledge.chunk_lineage (page_id);