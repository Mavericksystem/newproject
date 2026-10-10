import argparse
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
 
import psycopg
 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingestion"))
 
from align import ALIGNER_VERSION, Aligner  # noqa: E402
from chunker import CHUNKER_VERSION, chunk_wikitext  # noqa: E402
from content_store import ContentStore  # noqa: E402
from parse_wikitext import PARSER_VERSION  # noqa: E402
 
DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://wiki:wiki@localhost:5433/temporal")
BUILD_VERSION = f"{CHUNKER_VERSION}+{ALIGNER_VERSION}"


def verify_replay(revisions, versions, expected):
    """Rebuild every revision's chunk list from the versions and compare with the chunker's
    output. Catches any bug in alignment or interval closing before anything is written."""
    n = len(revisions)
    index = {rev_id: i for i, (rev_id, _, _) in enumerate(revisions)}
    got = [[] for _ in range(n)]
    for v in versions:
        start = index[v.from_rev]
        end = index[v.to_rev] if v.to_rev is not None else n
        row = (v.position, v.part_index, v.section_path, v.content_hash)
        for i in range(start, end):
            got[i].append(row)
    for i in range(n):
        if sorted(got[i]) != expected[i]:
            raise RuntimeError(f"replay mismatch at revision {revisions[i][0]} (index {i})")

        def build_page(revisions, get_text, progress_every=100):
    """revisions: list of (rev_id, ts, content_hash) in chronological order.
    get_text(content_hash) -> wikitext. Returns (lineages, versions)."""
    aligner = Aligner()
    plain_cache = {}  # section wikitext hash -> plain text, shared across revisions
    expected = []
    t0 = time.time()
    total = len(revisions)
    for n, (rev_id, _ts, content_hash) in enumerate(revisions, 1):
        try:
            wikitext = get_text(content_hash)
        except Exception as e:
            raise RuntimeError(f"could not read wikitext for revision {rev_id}") from e
        chunks = chunk_wikitext(wikitext, plain_cache=plain_cache)
        aligner.add_revision(rev_id, chunks)
        expected.append(sorted((c.position, c.part_index, c.section_path, c.content_hash) for c in chunks))
        if progress_every and n % progress_every == 0:
            el = time.time() - t0
            eta = el / n * (total - n)
            print(f"  {n}/{total} revisions  {el:.0f}s elapsed  ~{eta:.0f}s left", flush=True)
    lineages, versions = aligner.finish()
    verify_replay(revisions, versions, expected)
    return lineages, versions


def summarize(revisions, lineages, versions, seconds):
    by_lin = Counter(v.lineage_id for v in versions)
    last = {}
    for v in versions:  # versions are appended in time order, so the last one per lineage wins
        last[v.lineage_id] = v
    origins = Counter(l.origin for l in lineages)
    live = sum(1 for v in versions if v.to_rev is None)
    print(f"\nrevisions processed : {len(revisions)}")
    print(f"lineages            : {len(lineages)}  ({dict(origins)})")
    print(f"versions            : {len(versions)}  ({live} live at the latest revision)")
    print(f"build time          : {seconds:.1f}s")
    print("replay check        : OK (every revision rebuilt exactly from the versions)")
    print("\nmost-edited lineages (hand-check these):")
    for lid, cnt in by_lin.most_common(8):
        v = last[lid]
        state = "live" if v.to_rev is None else f"ended at rev {v.to_rev}"
        label = v.section_path or "(lead)"
        print(f"  lineage {lid:5}  {cnt:4} versions  part{v.part_index}  {state}  {label}")

        
def write_to_db(conn, page_id, started_at, revisions, lineages, versions, rebuild):
    ts_of = {rev_id: ts for rev_id, ts, _ in revisions}
    with conn.transaction():
        if rebuild:
            conn.execute("DELETE FROM knowledge.chunk_version WHERE page_id = %s", (page_id,))
            conn.execute("DELETE FROM knowledge.chunk_lineage WHERE page_id = %s", (page_id,))
        run_id = conn.execute(
            """INSERT INTO knowledge.build_run
               (page_id, parser_version, chunker_version, started_at, finished_at, status,
                revisions_processed, lineages_created, versions_created)
               VALUES (%s, %s, %s, %s, now(), 'done', %s, %s, %s) RETURNING id""",
            (page_id, PARSER_VERSION, BUILD_VERSION, started_at,
             len(revisions), len(lineages), len(versions)),
        ).fetchone()[0]
 
        db_id = {}  # Aligner local lineage id -> database id
        for lin in lineages:
            related = [db_id[r] for r in lin.related] or None
            db_id[lin.local_id] = conn.execute(
                """INSERT INTO knowledge.chunk_lineage
                   (page_id, first_rev_id, origin, related_lineage_ids, build_run_id)
                   VALUES (%s, %s, %s, %s::bigint[], %s) RETURNING id""",
                (page_id, lin.first_rev_id, lin.origin, related, run_id),
            ).fetchone()[0]
 
        rows = [
            (db_id[v.lineage_id], page_id, v.section_path, v.part_index, v.position, v.text,
             v.content_hash, v.from_rev, v.to_rev, ts_of[v.from_rev],
             ts_of[v.to_rev] if v.to_rev is not None else None, PARSER_VERSION, run_id)
            for v in versions
        ]
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO knowledge.chunk_version
                   (lineage_id, page_id, section_path, part_index, position, text, content_hash,
                    from_rev, to_rev, valid_during, parser_ver, build_run_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                           tstzrange(%s::timestamptz, %s::timestamptz, '[)'), %s, %s)""",
                rows,
            )
    return run_id