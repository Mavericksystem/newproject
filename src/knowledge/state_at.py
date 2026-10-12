import os
import sys
from datetime import datetime, timezone

DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://wiki:wiki@localhost:5433/temporal")


# --- pure logic -----------------------------------------------------------

def _live(v, t):
    return v["valid_from"] <= t and (v["valid_to"] is None or t < v["valid_to"])


def _order(v):
    return (v["position"], v["part_index"], v["lineage_id"])


def state_at(versions, t):
    """Versions live at time t, ordered by position, then part_index."""
    return sorted((v for v in versions if _live(v, t)), key=_order)


def changes_between(versions, t1, t2):
    """Compare the page state at t1 with the state at t2 (t1 <= t2).
    A passage that changes and changes back inside the window is not reported."""
    if t1 > t2:
        raise ValueError("t1 must not be after t2")
    before = {v["lineage_id"]: v for v in state_at(versions, t1)}
    after = {v["lineage_id"]: v for v in state_at(versions, t2)}
    added = sorted((v for k, v in after.items() if k not in before), key=_order)
    removed = sorted((v for k, v in before.items() if k not in after), key=_order)
    modified = [
        (before[k], after[k])
        for k in sorted(after, key=lambda k: _order(after[k]))
        if k in before and before[k]["content_hash"] != after[k]["content_hash"]
    ]
    return {"added": added, "removed": removed, "modified": modified}


# --- formatting (pure) ----------------------------------------------------

def _label(v):
    path = v["section_path"] or "(lead)"
    return f"{path} [part {v['part_index']}]" if v["part_index"] else path


def _preview(text, width, full):
    if full:
        return text
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[: max(width - 3, 1)] + "..."


def _in_section(v, section):
    p = v["section_path"]
    return p == section or p.startswith(section + " > ")


def format_at(title, page_id, when, live, rev, width=110, full=False, section=None):
    shown = [v for v in live if _in_section(v, section)] if section else live
    out = [f"{title} (page {page_id}) as of {when.isoformat()}"]
    if rev:
        out.append(f"in effect: revision {rev[0]} saved {rev[1].isoformat()}")
    else:
        out.append("in effect: no revision saved at or before this time")
    chars = sum(len(v["text"]) for v in shown)
    scope = f" in section '{section}'" if section else ""
    out.append(f"{len(shown)} chunks{scope}, {chars:,} characters")
    out.append("-" * 60)
    for v in shown:
        out.append(f"[{v['position']}] {_label(v)}  (lineage {v['lineage_id']}, since rev {v['from_rev']})")
        body = _preview(v["text"], width, full)
        out.append(("    " + body.replace("\n", "\n    ")) if full else "    " + body)
    return "\n".join(out)


def format_changes(title, page_id, t1, t2, ch, width=110, full=False):
    out = [
        f"{title} (page {page_id}) changes from {t1.isoformat()} to {t2.isoformat()}",
        f"added {len(ch['added'])}, removed {len(ch['removed'])}, modified {len(ch['modified'])}",
        "-" * 60,
    ]
    for v in ch["added"]:
        out.append(f"+ ADDED     {_label(v)}  (lineage {v['lineage_id']}, since rev {v['from_rev']})")
        out.append("    " + _preview(v["text"], width, full))
    for v in ch["removed"]:
        out.append(f"- REMOVED   {_label(v)}  (lineage {v['lineage_id']}, last seen in rev {v['from_rev']})")
        out.append("    " + _preview(v["text"], width, full))
    for old, new in ch["modified"]:
        out.append(f"~ MODIFIED  {_label(new)}  (lineage {new['lineage_id']}, rev {old['from_rev']} -> {new['from_rev']})")
        out.append("    before: " + _preview(old["text"], width, full))
        out.append("    after : " + _preview(new["text"], width, full))
    return "\n".join(out)


def parse_when(s):
    """'2013-06-01' or any ISO datetime; no offset means UTC."""
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --- database -------------------------------------------------------------

_COLS = ["id", "lineage_id", "section_path", "part_index", "position", "text", "content_hash",
         "valid_from", "valid_to", "from_rev", "to_rev"]


def load_versions(conn, page_id):
    """All versions of a page. Empty intervals (two revisions with the same timestamp) are
    skipped: such a version was live for zero time."""
    cur = conn.execute(
        """SELECT id, lineage_id, section_path, part_index, position, text, content_hash,
                  lower(valid_during), upper(valid_during), from_rev, to_rev
           FROM knowledge.chunk_version
           WHERE page_id = %s AND NOT isempty(valid_during)""",
        (page_id,),
    )
    return [dict(zip(_COLS, row)) for row in cur.fetchall()]


def find_page(conn, title, page_id):
    if page_id is not None:
        rows = conn.execute("SELECT page_id, title FROM raw.page WHERE page_id = %s", (page_id,)).fetchall()
    else:
        rows = conn.execute("SELECT page_id, title FROM raw.page WHERE title = %s AND ns = 0", (title,)).fetchall()
    if len(rows) != 1:
        raise SystemExit(f"expected exactly one matching page, found {len(rows)}")
    return rows[0]


def main(argv=None):
    import argparse

    import psycopg

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    common = argparse.ArgumentParser(add_help=False)
    which = common.add_mutually_exclusive_group(required=True)
    which.add_argument("--title", help="exact page title, namespace 0")
    which.add_argument("--page-id", type=int)
    common.add_argument("--dsn", default=DEFAULT_DSN)
    common.add_argument("--width", type=int, default=110, help="preview width in characters")
    common.add_argument("--full", action="store_true", help="print full chunk text")

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_at = sub.add_parser("at", parents=[common], help="page state at a time")
    p_at.add_argument("--when", required=True)
    p_at.add_argument("--section", help="only this section and its subsections")
    p_ch = sub.add_parser("changes", parents=[common], help="what changed between two times")
    p_ch.add_argument("--from", dest="t1", required=True)
    p_ch.add_argument("--to", dest="t2", required=True)
    args = ap.parse_args(argv)

    with psycopg.connect(args.dsn) as conn:
        page_id, title = find_page(conn, args.title, args.page_id)
        versions = load_versions(conn, page_id)
        if not versions:
            raise SystemExit(f"page {page_id} has no chunk versions; run build_chunks.py first")

        if args.cmd == "at":
            when = parse_when(args.when)
            live = state_at(versions, when)
            sql_ids = {
                r[0] for r in conn.execute(
                    "SELECT id FROM knowledge.chunk_version "
                    "WHERE page_id = %s AND valid_during @> %s::timestamptz", (page_id, when))
            }
            if sql_ids != {v["id"] for v in live}:
                raise SystemExit("MISMATCH: SQL range lookup and state_at() returned different chunks")
            rev = conn.execute(
                "SELECT rev_id, ts FROM raw.revision_default WHERE page_id = %s AND ts <= %s "
                "ORDER BY ts DESC, seq DESC LIMIT 1", (page_id, when)).fetchone()
            print(format_at(title, page_id, when, live, rev, args.width, args.full, args.section))
            print(f"\ncheck: SQL range lookup returned the same {len(sql_ids)} chunks")
        else:
            t1, t2 = parse_when(args.t1), parse_when(args.t2)
            if t1 > t2:
                raise SystemExit("--from must not be after --to")
            print(format_changes(title, page_id, t1, t2, changes_between(versions, t1, t2),
                                 args.width, args.full))


if __name__ == "__main__":
    main()