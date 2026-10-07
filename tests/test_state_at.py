
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



VERSIONS = [
    v(1, "", 0, 0, "h1a", "2020-01-01", "2020-06-01"),
    v(1, "", 0, 0, "h1b", "2020-06-01", None),
    v(2, "History", 1, 0, "h2", "2020-01-01", "2021-01-01"),
    v(3, "Uses", 2, 0, "h3", "2020-03-01", None),
    v(4, "Uses", 2, 1, "h4a", "2020-03-01", "2020-09-01"),
    v(4, "Uses", 2, 1, "h4b", "2020-09-01", None),
    v(5, "Safety", 3, 0, "h5a", "2020-01-01", "2020-04-01"),
    v(5, "Safety", 3, 0, "h5b", "2020-04-01", "2020-05-01"),
    v(5, "Safety", 3, 0, "h5a", "2020-05-01", None),
]


def ids(versions):
    return [x["lineage_id"] for x in versions]


def hashes(versions):
    return {x["lineage_id"]: x["content_hash"] for x in versions}


# --- state_at -------------------------------------------------------------

def test_before_first_revision_is_empty():
    assert state_at(VERSIONS, dt("2019-12-31")) == []


def test_start_of_interval_is_inclusive():
    assert ids(state_at(VERSIONS, dt("2020-01-01"))) == [1, 2, 5]


def test_ordered_by_position_then_part_index():
    s = state_at(VERSIONS, dt("2020-03-15"))
    assert ids(s) == [1, 2, 3, 4, 5]
    assert hashes(s) == {1: "h1a", 2: "h2", 3: "h3", 4: "h4a", 5: "h5a"}

