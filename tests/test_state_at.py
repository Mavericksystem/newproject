
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


def test_end_of_interval_is_exclusive():
    
    s = state_at(VERSIONS, dt("2020-06-01"))
    assert hashes(s)[1] == "h1b"
    assert ids(s).count(1) == 1


def test_removed_lineage_disappears_at_its_end():
    assert ids(state_at(VERSIONS, dt("2020-12-31"))) == [1, 2, 3, 4, 5]
    assert ids(state_at(VERSIONS, dt("2021-01-01"))) == [1, 3, 4, 5]


def test_open_ended_versions_are_live_in_the_future():
    s = state_at(VERSIONS, dt("2030-01-01"))
    assert ids(s) == [1, 3, 4, 5]
    assert hashes(s) == {1: "h1b", 3: "h3", 4: "h4b", 5: "h5a"}


def test_never_two_versions_of_one_lineage():
    for probe in ["2020-01-01", "2020-04-01", "2020-05-01", "2020-06-01",
                  "2020-09-01", "2021-01-01", "2025-01-01"]:
        got = ids(state_at(VERSIONS, dt(probe)))
        assert len(got) == len(set(got)), probe


def test_input_order_does_not_matter():
    a = state_at(VERSIONS, dt("2020-07-01"))
    b = state_at(list(reversed(VERSIONS)), dt("2020-07-01"))
    assert a == b


def test_returns_version_text():
    s = state_at(VERSIONS, dt("2020-07-01"))
    assert {x["lineage_id"]: x["text"] for x in s}[1] == "text-h1b"
