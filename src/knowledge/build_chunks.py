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