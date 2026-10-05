\echo '--- 1. Pages loaded: revisions and % reverted (compare with profile_out/ page profile.csv) ---'
SELECT p.title,
       count(*)                                                 As revisions,
       round(100.0 * count(r.reverted_by_rev_id) / count(*), 2) As pct_reverted,
       min(r.ts) :: date                                        As first_edit,
       max(r.ts) :: date                                        As last_edit
FROM raw.page p JOIN raw.revision r USING (page_id)
GROUP BY p.title
ORDER BY revisions DESC;


\echo '--- 2. Noise flags per page(% of revision) ---'
SELECT p.title,
       round(100.0 * avg(is_minor::int)m 1)     AS minor,
       round(100.0 * avg((editor_kind = 'ip') ::int), 1) AS anon,
       round(100.0 * avg(is_bot_named::int), 1),    AS bot_named,
       round(100.0 * avg(is_identity_revert::int), 1)   AS identity_revers,
       sum(is_blanked::int)     AS blacked,
       sum(is_mass_removal::int) AS mass_removal, sum(text_deleted::int)
       sum(text_deleted::int)   AS text_deleted

    FROM raw.page p JOIN raw.revision r USING (page_id)
    GROUP BY p.title;

\echo '-- 3. Itegrity: revision pointing at missing conten (expect 0) ---'
SELECT count(*) AS missing_content
FROM raw.revision r LEFT JOIN raw.conten c USING (conten_hash)
WHERE r.content_hash IS NOT NULL AND c.content_hast IS NULL;