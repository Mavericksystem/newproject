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

-- Wikitext lives in compressed files on disk, addressed by sha256 of the text.
-- This table is the index of those files (and lets us check integrity).
CREATE TABLE IF NOT EXISTS raw.content (
    content_hash text PRIMARY KEY, -- sha256 hex of UTF-8 wikitext
    size_bytes integer NOT NULL,
    compressed_bytes integer NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.revision (
    rev_id          bigint      PRIMARY KEY,
    page_id         bigint      NOT NULL REFERENCES raw.page(page_id),
    seq             integer     NOT NULL,            -- 0-based position in the dump for this page
    parent_id       bigint,                          -- may point outside the loaded set
    ts              timestamptz NOT NULL,            -- wiki time
    editor_kind     text        NOT NULL CHECK (editor_kind IN ('user', 'ip', 'deleted')),
    editor_name     text,                            -- registered users only; IPs are never stored
    comment         text,
    comment_deleted boolean     NOT NULL DEFAULT false,
    is_minor        boolean     NOT NULL DEFAULT false,
    sha1            text,                            -- as given by the dump (base-36)
    content_hash    text        REFERENCES raw.content(content_hash),  -- NULL when text deleted
    text_bytes      integer     NOT NULL DEFAULT 0,
    text_deleted    boolean     NOT NULL DEFAULT false,
    model           text,
    format          text,

-- Noise flags: computed by the loader, never used to delete anything.


is_bot_named        boolean NOT NULL DEFAULT false,  -- name heuristic, undercounts
    is_null_edit        boolean NOT NULL DEFAULT false,  -- identical to previous revision
    is_identity_revert  boolean NOT NULL DEFAULT false,  -- restores an earlier identical state
    reverts_to_rev_id   bigint,                          -- the revision it restored
    reverted_by_rev_id  bigint,                          -- the revert that later undid this one
    is_blanked          boolean NOT NULL DEFAULT false,  -- text size 0
    is_mass_removal     boolean NOT NULL DEFAULT false,  -- size < 10% of previous revision
    comment_looks_revert boolean NOT NULL DEFAULT false,

    ingest_run_id   bigint      REFERENCES raw.ingest_run(id),
    UNIQUE (page_id, seq)
);

CREATE INDEX IF NOT EXISTS revision_page_ts_idx ON raw.revision (page_id, ts);

CREATE INDEX IF NOT EXISTS revision_content_idx ON raw.revision (content_hash);

CREATE INDEX IF NOT EXISTS revision_sha1_idx ON raw.revision (sha1);

-- Proposed default for downstream queries: revisions that survived and have text.
-- Reverted, null-edit and text-deleted revisions stay in raw.revision for audit.
CREATE OR REPLACE VIEW raw.revision_default AS
SELECT *
FROM raw.revision
WHERE
    reverted_by_rev_id IS NULL
    AND NOT is_null_edit
    AND NOT text_deleted
    AND content_hash IS NOT NULL;