-- Sanity checks after loading. Run:
--   docker exec -i temporal-kb-db psql -U wiki -d temporal < db/queries/checks.sql

\echo '--- 1. Pages loaded: revisions and % reverted (compare with profile_out/page_profile.csv) ---'
SELECT p.title,
       count(*)                                                        AS revisions,
       round(100.0 * count(r.reverted_by_rev_id) / count(*), 2)        AS pct_reverted,
       min(r.ts)::date                                                 AS first_edit,
       max(r.ts)::date                                                 AS last_edit
FROM raw.page p JOIN raw.revision r USING (page_id)
GROUP BY p.title
ORDER BY revisions DESC;

\echo '--- 2. Noise flags per page (% of revisions) ---'
SELECT p.title,
       round(100.0 * avg(is_minor::int), 1)             AS minor,
       round(100.0 * avg((editor_kind = 'ip')::int), 1) AS anon,
       round(100.0 * avg(is_bot_named::int), 1)         AS bot_named,
       round(100.0 * avg(is_identity_revert::int), 1)   AS identity_reverts,
       sum(is_blanked::int)                             AS blanked,
       sum(is_mass_removal::int)                        AS mass_removal,
       sum(text_deleted::int)                           AS text_deleted
FROM raw.page p JOIN raw.revision r USING (page_id)
GROUP BY p.title;

\echo '--- 3. Integrity: revisions pointing at missing content (expect 0) ---'
SELECT count(*) AS missing_content
FROM raw.revision r LEFT JOIN raw.content c USING (content_hash)
WHERE r.content_hash IS NOT NULL AND c.content_hash IS NULL;

\echo '--- 4. Integrity: gaps in seq per page (expect 0 rows) ---'
SELECT page_id, max(seq) + 1 AS expected, count(*) AS actual
FROM raw.revision GROUP BY page_id HAVING max(seq) + 1 <> count(*);

\echo '--- 5. Storage ---'
SELECT count(*)                                  AS unique_texts,
       pg_size_pretty(sum(size_bytes))           AS raw_size,
       pg_size_pretty(sum(compressed_bytes))     AS compressed_size,
       round(sum(size_bytes)::numeric / sum(compressed_bytes), 1) AS ratio
FROM raw.content;

\echo '--- 6. Latest ingest runs ---'
SELECT id, status, pages_loaded, revisions_loaded, started_at, finished_at, selection
FROM raw.ingest_run ORDER BY id DESC LIMIT 5;