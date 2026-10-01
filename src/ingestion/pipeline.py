import argparse
import bz2
import csv
import gzip
import statistics
import sys
import time

from lxml import etree


def open_dump(path):
    if path.endswith(".bz2"):
        return bz2.open(path, "rb")
    if path.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")


def text_of(elem, tag):
    child = elem.find(tag)
    return child.text if child is not None else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--out", default="page_stats.csv")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    rows = []
    ns_uri = None
    # per-page accumulators (revisions end before their page ends)
    rev_count = 0
    first_ts = last_ts = None
    total_bytes = 0
    t0 = time.time()

    with open_dump(args.dump) as f:
        context = etree.iterparse(f, events=("start", "end"), huge_tree=True)
        for event, elem in context:
            if ns_uri is None:
                # first element is <mediawiki xmlns="...">; grab its namespace
                ns_uri = etree.QName(elem).namespace
                ns = "{%s}" % ns_uri if ns_uri else ""
            if event != "end":
                continue

            tag = elem.tag

            if tag == ns + "revision":
                rev_count += 1
                ts = text_of(elem, ns + "timestamp")
                if ts:
                    # ISO-8601 UTC strings sort lexicographically
                    if first_ts is None or ts < first_ts:
                        first_ts = ts
                    if last_ts is None or ts > last_ts:
                        last_ts = ts
                t = elem.find(ns + "text")
                if t is not None:
                    declared = t.get("bytes")
                    total_bytes += int(declared) if declared else len((t.text or "").encode())
                elem.clear()

            elif tag == ns + "page":
                rows.append({
                    "page_id": text_of(elem, ns + "id"),  # direct child only
                    "ns": text_of(elem, ns + "ns"),
                    "title": text_of(elem, ns + "title"),
                    "is_redirect": elem.find(ns + "redirect") is not None,
                    "revisions": rev_count,
                    "first_ts": first_ts,
                    "last_ts": last_ts,
                    "total_text_bytes": total_bytes,
                })
                rev_count, first_ts, last_ts, total_bytes = 0, None, None, 0

                # free memory: clear page and drop processed siblings
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                if len(rows) % 100 == 0:
                    print(f"  {len(rows)} pages... ({time.time() - t0:.0f}s)", file=sys.stderr)

    if not rows:
        print("No pages found. Is this a MediaWiki XML export?")
        return

    rows.sort(key=lambda r: r["revisions"], reverse=True)
    with open(args.out, "w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    counts = [r["revisions"] for r in rows]
    single = sum(1 for c in counts if c == 1)
    print(f"\nParsed in {time.time() - t0:.0f}s -> {args.out}")
    print(f"Pages: {len(rows)}   Revisions: {sum(counts)}")
    print(f"Revisions/page: median={statistics.median(counts)}  mean={statistics.mean(counts):.1f}  max={max(counts)}")
    print(f"Pages with exactly 1 revision: {single} ({100 * single / len(rows):.0f}%)")
    print(f"Redirects: {sum(1 for r in rows if r['is_redirect'])}")
    if single == len(rows):
        print("\n=> Every page has 1 revision: this is a CURRENT-ONLY dump, not full history.")

    print(f"\nTop {args.top} pages by revision count:")
    print(f"{'revs':>7}  {'first':10}  {'last':10}  title")
    for r in rows[: args.top]:
        print(f"{r['revisions']:>7}  {(r['first_ts'] or '')[:10]:10}  {(r['last_ts'] or '')[:10]:10}  {r['title']}")


if __name__ == "__main__":
    main()