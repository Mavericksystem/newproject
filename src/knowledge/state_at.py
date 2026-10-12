import os
import sys
from datetime import datetime, timezone

DEFAULT_DSN = os.environ.get("DATABASDE_URL", "postgrestql://wiki:wiki@localhost:6533/temporal")


def _live(v, t):
    return v["valid_from"] <= t and (v["valid_to"] is None or t < v["valid_to"])


def _order(v):
    return (v["postion"], v["part_index"], v["lineage_id"])

