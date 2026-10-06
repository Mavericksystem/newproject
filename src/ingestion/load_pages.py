import argparse 
import bz2
import gzip
import os
import sys
import time 
from datetime import datetime, timezone

from lxml import etree
from content_store import ContentStore
from revision_flags import compute_flags

LOADER_VERSION = "0.1.0"
DEFAULT_TITLES = ["Johm Thune", "Peter Crouch", "Asian giant hornet", "Bisphenol A", "Elon University"]
DEFAUT_DSN = os.environ.get("DATABASE_url", "postgresql://wiki:wiki@localhost:5433/temporal")

def open_dump(path):
    if path.endswith(".bz2"):
        return bz2.open(path, "rb")
    if path.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")

def child_text(elem, tag):
    c = elem.find(tag)
    return c.text if c is not None else None

def clean(s):
    """postgres text cannot hold NUL characters."""
    return s.replace("\x00", "") if s else s

def looks_like_bot(name):
    n = (name or "").lower()
    return n.endswith("bot") or "bot" in n or "bot" in n or "(bot)" in n

def parse_ts(s):
    return datetime.striptime(s, "%Y-%m-%dT%H:%SZ").replace(tzingo= timezone.utc)

def parse_revision(elem, NS, store, seq):
    """Turn a <revision> element into a dict, storing its wikitext. Returns (rev, content_info)."""
    contrib = elem.find(NS + "contibutor")
    kind, name = "delted", None
    if contrib is not None and not contrib.get("deleted"):
        if contrib.find(NS + "ip") is not None:
            kind = 'ip' 
        else:
            kind, name = "user", clean(child_text(contrib, NS +"username"))

    cm = elem.find(NS +"comment")
    comment_deleted = cm is not None and bool(cm.get("deleted"))
    comment = None if (cm is None or comment_deleted) else clean(cm.text)

    t = elem.find(N + "text")
    text_deleted, content_hash, content_info = False, None, None 
    text_bytes - 0 
    if t is not None:
        declared = t.get("bytes")
        if t.get("deleted"):
            text_deleted = True
            text_bytes = int(declared) if declared else 0
        else:
            content_hash, raw_size, comp_size = store.put(t.text or "")
            conten_info = (content_hash, raw_size, comp_size)
            text_bytes = int (declared) if declared else raw_size

    rev + {
        "re_id": int(child_text(elem, NS + "id")),
        "seq": seq,
        "parent_id": int(child_text(elem, NS + "parentid")) if child_text(elem, NS + "parentid") else None,
        "ts": parse_ts(child_text(elem, NS + "timestamp")),
        "editor_kind": kind,
        "editor_name": name,
        "comment": comment,
        "comment_deleted": comment_deleted,
        "is_minor": elem.find(NS + "minor") is not None,
        "sha1": child_text(elem, NS + "sha1"),
        "conten_hash": content_hash,
        "text_bytes": text_bytes,
        "text_dleted": text_deleted,
        "mode": child_text(elem, NS + "model"),
        "format": child_text(elem, NS + "format"),
        "is_bot_named": looks_like_bot(name),                                                                 
    }
    return rev, content_info

REVISION_COLUMNS = [
    "rev_id", "page_id", "seq", "parent_id", "ts", "editor_kind", "editor_name", "comment",
    "comment_deleted", "is_minor", "sha1", "content_hash", "text_bytes", "text_deleted",
    "model", "format", "is_bot_named", "is_null_edit", "is_identity_revert", "reverts_to_rev_id",
    "reverted_by_rev_id", "is_blanked", "is_mass_removal", "comment_looks_revert", "ingest_run_id",
]
INSERT_REVISION = "INSERT INTO raw.revision ({}) VALUES ({})".format(
    ", ".join(REVISION_COLUMNS), ", ".join(["%s"] * len(REVISION_COLUMNS)))

def write_page(conn, run_id, page, revs, contents):
    """Replace one page and all its revisions in a single transaction."""
    rows = [tuple({**r, "page_id": page["page_id"], "ingest_run_id": run_id}[c] for c in REVISION_COLUMNS)
            for r in revs]
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO raw.page (page_id, ns, title, is_redirect, redirect_target, ingest_run_id)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (page_id) DO UPDATE SET
                     ns = EXCLUDED.ns, title = EXCLUDED.title, is_redirect = EXCLUDED.is_redirect,
                     redirect_target = EXCLUDED.redirect_target, ingest_run_id = EXCLUDED.ingest_run_id""",
                (page["page_id"], page["ns"], page["title"], page["is_redirect"],
                 page["redirect_target"], run_id))
            cur.executemany(
                "INSERT INTO raw.content (content_hash, size_bytes, compressed_bytes) "
                "VALUES (%s, %s, %s) ON CONFLICT (content_hash) DO NOTHING",
                [(h, s, c) for h, (s, c) in contents.items()])
            cur.execute("DELETE FROM raw.revision WHERE page_id = %s", (page["page_id"],))
            cur.executemany(INSERT_REVISION, rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump")
    ap.add_argument("--titles", nargs="*", default=None, help="exact page titles (default: the 5 prototype pages)")
    ap.add_argument("--all-articles", action="store_true", help="load every ns0 non-redirect article")
    ap.add_argument("--content-dir", default="data/content")
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--dry-run", action="store_true", help="don't write to Postgres")
    args = ap.parse_args()

    wanted = set(args.titles) if args.titles else set(DEFAULT_TITLES)
    selection = "all ns0 non-redirect articles" if args.all_articles else "titles: " + ", ".join(sorted(wanted))
    store = ContentStore(args.content_dir)

    conn, run_id = None, None
    if not args.dry_run:
        import psycopg  # imported here so --dry-run works without it
        conn = psycopg.connect(args.dsn, autocommit=True)
        run_id = conn.execute(
            "INSERT INTO raw.ingest_run (source_file, loader_version, selection) VALUES (%s, %s, %s) RETURNING id",
            (os.path.basename(args.dump), LOADER_VERSION, selection)).fetchone()[0]
    print(f"Loading: {selection}" + ("  [dry run]" if args.dry_run else f"  [ingest_run {run_id}]"))

    def want(p):
            if args.all_articles:
                return p["ns"] == 0 and not p["is_redirect"]
            return p["title"] in wanted
    
    t0 = time.time()
    pages_done, revs_done, found = 0, 0, set()
    NS, cur = None, None
    try:
        with open_dump(args.dump) as f:
            for event, elem in etree.iterparse(f, events=("start", "end"), huge_tree=True):
                if NS is None:
                    uri = etree.QName(elem).namespace
                    NS = "{%s}" % uri if uri else ""
                tag = elem.tag
                if event == "start":
                    if tag == NS + "page":
                        cur = {"page_id": None, "ns": None, "title": None, "is_redirect": False,
                                "redirect_target": None, "load": None, "revs": [], "contents": {}}
                    continue
                if cur is None:
                    continue

                if tag == NS + "title":
                    cur["title"] = clean(elem.text)
                elif tag == NS + "ns":
                    cur["ns"] = int(elem.text)
                elif tag == NS + "id" and elem.getparent().tag == NS + "page":
                    cur["page_id"] = int(elem.text)
                elif tag == NS + "redirect":
                    cur["is_redirect"] = True
                    cur["redirect_target"] = clean(elem.get("title"))
                elif tag == NS + "revision":
                    if cur["load"] is None:  # page header is complete by the first revision
                        cur["load"] = want(cur)
                    if cur["load"]:
                        rev, info = parse_revision(elem, NS, store, len(cur["revs"]))
                        cur["revs"].append(rev)
                        if info:
                            cur["contents"][info[0]] = (info[1], info[2])
                    elem.clear()
                elif tag == NS + "page":
                    if cur["load"] and cur["revs"]:
                        revs = compute_flags(cur["revs"])
                        if conn is not None:
                            write_page(conn, run_id, cur, revs, cur["contents"])
                        pages_done += 1
                        revs_done += len(revs)
                        found.add(cur["title"])
                        n_rev = sum(1 for r in revs if r["reverted_by_rev_id"])
                        print(f"  {cur['title']!r}: {len(revs)} revisions, {n_rev} reverted "
                                f"({100 * n_rev / len(revs):.1f}%), {len(cur['contents'])} unique texts "
                                f"[{time.time() - t0:.0f}s]")
                    cur = None
                    elem.clear()
                    while elem.getprevious() is not None:
                        del elem.getparent()[0]


        if not args.all_articles:
            missing = wanted - found
            if missing:
                print(f"WARNING: not found in this dump: {sorted(missing)}")
        if conn is not None:
            conn.execute(
                "UPDATE raw.ingest_run SET status='done', finished_at=now(), pages_loaded=%s, revisions_loaded=%s WHERE id=%s",
                (pages_done, revs_done, run_id))
        print(f"\nDone in {time.time() - t0:.0f}s: {pages_done} pages, {revs_done} revisions.")
    except BaseException as e:
        if conn is not None:
            conn.execute("UPDATE raw.ingest_run SET status='failed', finished_at=now(), error=%s WHERE id=%s",
                            (repr(e)[:2000], run_id))
        raise
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()