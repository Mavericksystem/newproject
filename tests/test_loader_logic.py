import sys, tempfile, os, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "ingestion"))
from revision_flags import compute_flags
from content_store import ContentStore
import load_pages

def mk(rid, sha, size, comment=None, deleted=False):
    return {"rev_id": rid, "sha1": sha, "text_bytes": size, "comment": comment, "text_deleted": deleted}

# --- flags -------------------------------------------------------------
revs = compute_flags([
    mk(1, "A", 100), mk(2, "B", 110), mk(3, "V", 9),            # 3 = vandalism (mass removal)
    mk(4, "B", 110, "Reverting vandalism"),                      # revert to 2, undoes 3
    mk(5, "B", 110),                                             # null edit
    mk(6, "E", 0, "blank"),                                      # blanked
    mk(7, "B", 110, "rv blanking"),                              # revert to 5, undoes 6
    mk(8, None, 50, deleted=True),                               # deleted text, no sha1
    mk(9, "F", 120),
])
by = {r["rev_id"]: r for r in revs}
assert by[3]["reverted_by_rev_id"] == 4 and by[3]["is_mass_removal"]
assert by[4]["is_identity_revert"] and by[4]["reverts_to_rev_id"] == 2 and by[4]["comment_looks_revert"]
assert by[5]["is_null_edit"] and not by[5]["is_identity_revert"]
assert by[6]["is_blanked"] and by[6]["reverted_by_rev_id"] == 7
assert by[7]["is_identity_revert"] and by[7]["reverts_to_rev_id"] == 5 and by[7]["comment_looks_revert"]
assert not by[8]["is_blanked"] and not by[8]["is_mass_removal"]
assert [r["rev_id"] for r in revs if r["reverted_by_rev_id"]] == [3, 6]
print("flags OK")