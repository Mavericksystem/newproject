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