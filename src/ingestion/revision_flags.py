import re

REVERT_COMMENT = re.compile(r"\b(revert(ed)?|rv|rvv|undid|undo|rollback|reverting)\b", re.I)


def compute_flags(revs):
    for r in revs:
        r["is_null_edit"] = False
        r["is_identity_revert"] = False
        r["reverts_to_rev_id"] = None
        r["reverted_by_rev_id"] = None
        r["is_blanked"] = r["text_bytes"] == 0 and not r.get("text_deleted")
        r["is_mass_removal"] = False
        r["comment_looks_revert"] = bool(r.get("comment") and REVERT_COMMENT.search(r["comment"]))
