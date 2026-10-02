import argparse
import bz2
import csv
import gzip
import json
import random
import re
import statistics
import sys
import time
from array import array
from collections import Counter
from pathlib import Path
 
from lxml import etree
 
DEFAULT_SAMPLES = ["John Thune", "Peter Crouch", "Asian giant hornet", "Bisphenol A", "Elon University"]
REVERT_COMMENT = re.compile(r"\b(revert(ed)?|rv|rvv|undid|undo|rollback|reverting)\b", re.I)
INFOBOX = re.compile(r"\{\{\s*infobox", re.I)
 
 
def open_dump(path):
    if path.endswith(".bz2"):
        return bz2.open(path, "rb")
    if path.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")
 
 
def child_text(elem, tag):
    c = elem.find(tag)
    return c.text if c is not None else None
 
 
def looks_like_bot(name):
    n = (name or "").lower()
    return n.endswith("bot") or " bot" in n or "bot " in n or "(bot)" in n

 class Agg:
    """Counters that can be merged: one per page, then ALL and ARTICLES."""
 
    def __init__(self):
        self.pages = 0
        self.revisions = 0
        self.minor = 0
        self.anon = 0
        self.bot_named = 0
        self.reverts = 0          # revisions restoring an earlier identical state
        self.reverted = 0         # revisions undone by a later revert
        self.null_edits = 0       # identical to the immediately previous revision
        self.revert_comment = 0   # edit summary looks like a revert
        self.blanked = 0          # revision text size == 0
        self.mass_removal = 0     # size dropped below 10% of previous
        self.deleted_text = 0
        self.deleted_contrib = 0
        self.no_comment = 0
        self.bytes_total = 0
        self.bytes_dup_in_page = 0
        self.years = Counter()
        self.sizes = array("q")
        self.abs_deltas = array("q")
 
    def merge(self, o):
        for k, v in o.__dict__.items():
            if isinstance(v, int):
                setattr(self, k, getattr(self, k) + v)
        self.years.update(o.years)
        self.sizes.extend(o.sizes)
        self.abs_deltas.extend(o.abs_deltas)

def pctiles(arr, ps=(50, 90, 99)):
    if not len(arr):
        return {}
    s = sorted(arr)
    out = {f"p{p}": s[min(len(s) - 1, int(len(s) * p / 100))] for p in ps}
    out["max"] = s[-1]
    return out
 
 
def share(a, b):
    return round(100 * a / b, 2) if b else 0.0
 
 
def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)[:60]

def summarize(name, a):
    n = a.revisions
    d = {
        "pages": a.pages,
        "revisions": n,
        "pct_minor": share(a.minor, n),
        "pct_anonymous_ip": share(a.anon, n),
        "pct_bot_named": share(a.bot_named, n),
        "pct_identity_reverts": share(a.reverts, n),
        "pct_reverted_revisions": share(a.reverted, n),
        "pct_null_edits": share(a.null_edits, n),
        "pct_revert_in_comment": share(a.revert_comment, n),
        "pct_no_comment": share(a.no_comment, n),
        "blanked_revisions": a.blanked,
        "mass_removal_revisions": a.mass_removal,
        "deleted_text_revisions": a.deleted_text,
        "deleted_contributor_revisions": a.deleted_contrib,
        "revision_size_bytes": pctiles(a.sizes),
        "abs_size_change_bytes": pctiles(a.abs_deltas),
        "total_wikitext_gb": round(a.bytes_total / 1e9, 3),
        "pct_bytes_duplicate_within_page": share(a.bytes_dup_in_page, a.bytes_total),
        "revisions_per_year": dict(sorted(a.years.items())),
    }
    print(f"\n===== {name} =====")
    for k, v in d.items():
        if k == "revisions_per_year":
            continue
        print(f"{k:34} {v}")
    print("revisions per year:")
    for y, c in sorted(a.years.items()):
        print(f"  {y}  {c:>8}  {'#' * int(50 * c / max(a.years.values()))}")
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--outdir", default="profile_out")
    ap.add_argument("--sample-titles", nargs="*", default=DEFAULT_SAMPLES)
    ap.add_argument("--random-samples", type=int, default=3)
    args = ap.parse_args()
 
    outdir = Path(args.outdir)
    (outdir / "samples").mkdir(parents=True, exist_ok=True)
    sample_titles = set(args.sample_titles)
    rng = random.Random(42)
 
    all_agg, art_agg = Agg(), Agg()
    ns_pages, ns_redirects, ns_revs = Counter(), Counter(), Counter()
    models = Counter()
    global_seen = set()
    global_unique_bytes = 0
    rows = []
 
    NS = None
    cur_title = None
    # per-page state
    pa = Agg()
    seq_pos = {}                 # sha1 -> last index in this page
    reverted_flags = bytearray()
    seen_in_page = set()
    prev_size = None
    idx = 0
    last_text = None
    editors = Counter()
    sample_first = sample_last = None
    sample_rand = []
    t0 = time.time()

    with open_dump(args.dump) as f:
        for event, elem in etree.iterparse(f, events=("start", "end"), huge_tree=True):
            if NS is None:
                uri = etree.QName(elem).namespace
                NS = "{%s}" % uri if uri else ""
            if event != "end":
                continue
            tag = elem.tag
 
            if tag == NS + "title":
                cur_title = elem.text
 
            elif tag == NS + "revision":
                rid = child_text(elem, NS + "id")
                ts = child_text(elem, NS + "timestamp") or ""
                sha1 = child_text(elem, NS + "sha1")
                models[(child_text(elem, NS + "model"), child_text(elem, NS + "format"))] += 1
 
                contrib = elem.find(NS + "contributor")
                uname = None
                if contrib is None or contrib.get("deleted"):
                    pa.deleted_contrib += 1
                elif contrib.find(NS + "ip") is not None:
                    pa.anon += 1
                else:
                    uname = child_text(contrib, NS + "username")
                    if looks_like_bot(uname):
                        pa.bot_named += 1
                    if uname:
                        editors[uname] += 1

                        if elem.find(NS + "minor") is not None:
                    pa.minor += 1
 
                cm = elem.find(NS + "comment")
                ctext = cm.text if cm is not None and not cm.get("deleted") else None
                if not ctext:
                    pa.no_comment += 1
                elif REVERT_COMMENT.search(ctext):
                    pa.revert_comment += 1
 
                t = elem.find(NS + "text")
                size = 0
                text = None
                if t is not None:
                    text = t.text
                    if t.get("deleted"):
                        pa.deleted_text += 1
                    declared = t.get("bytes")
                    size = int(declared) if declared else len((text or "").encode())
                pa.sizes.append(size)
                pa.bytes_total += size
                pa.revisions += 1
                pa.years[ts[:4]] += 1
                if size == 0:
                    pa.blanked += 1
                if prev_size is not None:
                    pa.abs_deltas.append(abs(size - prev_size))
                    if prev_size > 0 and size < 0.1 * prev_size:
                        pa.mass_removal += 1
                prev_size = size