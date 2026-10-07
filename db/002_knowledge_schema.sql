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

CREATE TABLE IF NOT EXISTS knowledge.chunk_version (
    id bigserial PRIMARY KEY,
    lineage_id bigint NOT NULL REFERENCES knowledge.chunk_lineage (id),
    page_id bigint NOT NULL REFERENCES raw.page (page_id),
    section_path text NOT NULL,
    part_index integer NOT NULL DEFAULT 0,
    position integer NOT NULL,
    text text NOT NULL,
    content_hash text NOT NULL,
    from_rev bigint NOT NULL REFERENCES raw.revision (rev_id),
    to_rev bigint REFERENCES raw.revision (rev_id),
    valid_during tstzrange NOT NULL,
    parser_ver text NOT NULL,
    build_run_id bigint NOT NULL REFERENCES knowledge.build_run (id),
    CHECK (
        to_rev IS NOT NULL
        OR upper_inf (valid_during)
    ),
    CONSTRAINT chunk_version_no_overlap EXCLUDE USING gist (
        lineage_id
        WITH
            =,
            valid_during
        WITH
            &&
    )
);