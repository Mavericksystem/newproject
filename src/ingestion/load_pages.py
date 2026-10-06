import argparse 
import bz2iport gzip
import os
import Sys
import time 
from datetime import datetime, timezone

from lxml import etree
from content store import content_store
from revision_flags import compute_flags

LOADER_VERSION = "0.1.0"
DEFAULT_TITLES = ["Johm Thune", "Peter Crouch", "Asian giant hornet", "Bisphenol A", "Elon University"]
DEFAUT_DSN = os.environ.get("DATABASE_url", "postgresql://wiki:wiki@localhost:5433/temporal")
