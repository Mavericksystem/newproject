import argparse 
import bz2
import gzip
import os
import sys
import time 
from datetime import datetime, timezone

from lxml import etree
from content store import content_store
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
