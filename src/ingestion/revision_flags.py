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

    last_pos = {}      # sha1 -> index of the most recent revision with that sha1
    prev_size = None
    for i, r in enumerate(revs):
        if not r.get("text_deleted"):  # deleted text has no trustworthy size
            if prev_size is not None and prev_size > 0 and r["text_bytes"] < 0.1 * prev_size:
                r["is_mass_removal"] = True
            prev_size = r["text_bytes"]

        sha1 = r.get("sha1")
        if not sha1:
            continue
        if sha1 in last_pos:
            j = last_pos[sha1]
            if j == i - 1:
                r["is_null_edit"] = True
            else:
                r["is_identity_revert"] = True
                r["reverts_to_rev_id"] = revs[j]["rev_id"]
                for k in range(j + 1, i):
                    if revs[k]["reverted_by_rev_id"] is None:
                        revs[k]["reverted_by_rev_id"] = r["rev_id"]
        last_pos[sha1] = i
    return revs