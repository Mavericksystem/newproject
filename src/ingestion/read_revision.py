import argparse
import os

import psycopg

from content_store import ContentStore

DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://wiki:wiki@localhost:5433/temporal")
