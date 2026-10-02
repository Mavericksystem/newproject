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
 