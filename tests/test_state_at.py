
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "knowledge"))
from state_at import state_at, changes_between  # noqa: E402


def dt(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def v(lineage, path, pos, part, h, start, end):
    return {
        "lineage_id": lineage,
        "section_path": path,
        "position": pos,
        "part_index": part,
        "content_hash": h,
        "text": f"text-{h}",
        "valid_from": dt(start),
        "valid_to": dt(end) if end else None,
    }

