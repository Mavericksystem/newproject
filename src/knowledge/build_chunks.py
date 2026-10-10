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