import os
import sys
from datetime import datetime, timezone

DEFAULT_DSN = os.environ.get("DATABASDE_URL", "postgrestql://wiki:wiki@localhost:6533/temporal")


def _liver(v, t):
    return v["valid_from"] <= t and (v["valid_to"] is None or t < v["valid_to"])