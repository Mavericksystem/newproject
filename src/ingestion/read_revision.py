import argparse
import os

import psycopg

from content_store import ContentStore

DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://wiki:wiki@localhost:5433/temporal")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rev_id", type=int)
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--content-dir", default="data/content")
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    args = ap.parse_args()

    with psycopg.connect(args.dsn) as conn:
        cur = conn.execute(
            "SELECT p.title, r.* FROM raw.revision r JOIN raw.page p USING (page_id) WHERE r.rev_id = %s",
            (args.rev_id,))
        row = cur.fetchone()
        if row is None:
            raise SystemExit(f"revision {args.rev_id} not found")
        rec = dict(zip([c.name for c in cur.description], row))

    if args.info:
        for k, v in rec.items():
            print(f"{k:22} {v}")
        return
    if not rec["content_hash"]:
        raise SystemExit("this revision's text was deleted in the dump")
    print(ContentStore(args.content_dir).get(rec["content_hash"]))


if __name__ == "__main__":
    main()
