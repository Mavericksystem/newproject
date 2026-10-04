/
echo '--- 1. Pages loaded: revisions and % reverted (compare with profile_out/ page profile.csv) ---'
SELECT p.title,
       count(*)                                 As revisions,
       round(100.0 * count(r.reverted_by_rev_id) / count(*), 2) As pct_reverted,
       min(r.ts) :: date As first_edit,
       max(r.ts) :: date As last_edit
FROM raw.page p JOIN raw.revision r USING (page_id)
GROUP BY p.title
ORDER BY revisions DESC;