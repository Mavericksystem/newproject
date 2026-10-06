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

# --- content store -----------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    s = ContentStore(d)
    h1, n1, c1 = s.put("héllo wikitext {{x}} 日本")
    h2, n2, c2 = s.put("héllo wikitext {{x}} 日本")          # same text -> same file, no-op
    assert h1 == h2 and n1 == n2 and c1 == c2
    assert s.get(h1) == "héllo wikitext {{x}} 日本"
    he, ne, _ = s.put("")
    assert s.get(he) == "" and ne == 0
    n_files = sum(len(f) for _, _, f in os.walk(d))
    assert n_files == 2, n_files
    print("content store OK (dedupe, unicode, empty text, round-trip)")

    # --- write_page builds correct rows (fake connection) ------------------
class FakeCur:
    def __init__(self, log): self.log = log
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params=None): self.log.append(("execute", sql.split()[0], params))
    def executemany(self, sql, rows): rows = list(rows); self.log.append(("many", sql[:40], rows))
class FakeTx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
class FakeConn:
    def __init__(self): self.log = []
    def transaction(self): return FakeTx()
    def cursor(self): return FakeCur(self.log)

conn = FakeConn()
page = {"page_id": 100, "ns": 0, "title": "T", "is_redirect": False, "redirect_target": None}
for r in revs:
    r.update({"seq": r["rev_id"] - 1, "parent_id": None, "ts": None, "editor_kind": "user", "editor_name": "n",
              "comment_deleted": False, "is_minor": False, "content_hash": None, "model": "wikitext",
              "format": "text/x-wiki", "is_bot_named": False})
load_pages.write_page(conn, 7, page, revs, {"abc": (10, 5)})
ins = [e for e in conn.log if e[0] == "many" and "raw.revision" in e[1]][0][2]
assert len(ins) == 9 and all(len(t) == len(load_pages.REVISION_COLUMNS) for t in ins)
assert [e[1] for e in conn.log if e[0] == "execute"] == ["INSERT", "DELETE"]
print("write_page row mapping OK")