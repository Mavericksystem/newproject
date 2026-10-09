from dataclasses import dataclass, field
from difflib import SequenceMatcher


ALIGNER_VERSION = "align-1"
FUZZY_MIN_RATIO = 0.6
FUZZY_MAX_PAIRS = 400


@dataclass
class Lineage:
    local_id: int            
    first_rev_id: int
    origin: str = "new"      
    related: list = field(default_factory=list) 


@dataclass
class Version:
    lineage_id: int          # Lineage.local_id
    section_path: str
    part_index: int
    position: int
    text: str
    content_hash: str
    from_rev: int
    to_rev: int | None = None 


def _ratio(a, b):
    sm = SequenceMatcher(None, a, b, autojunk=False)
    if sm.real_quick_ratio() < FUZZY_MIN_RATIO or sm.quick_ratio() < FUZZY_MIN_RATIO:
        return 0.0
    return sm.ratio()


def _state(v):
    return (v.content_hash, v.section_path, v.part_index, v.position)


class Aligner:
    def __init__(self):
        self.lineages = []
        self.versions = []
        self._live = {}  
        self._key = {}   

    def _open(self, lineage_id, chunk, rev_id):
        v = Version(
            lineage_id=lineage_id,
            section_path=chunk.section_path,
            part_index=chunk.part_index,
            position=chunk.position,
            text=chunk.text,
            content_hash=chunk.content_hash,
            from_rev=rev_id,
        )
        self.versions.append(v)
        self._live[lineage_id] = v
        self._key[lineage_id] = chunk.key
        return v

    def _new_lineage(self, rev_id, origin, related):
        lin = Lineage(len(self.lineages) + 1, rev_id, origin, list(related))
        self.lineages.append(lin)
        return lin.local_id



    def add_revision(self, rev_id, chunks):
        """Align one revision's chunks against the current live state."""
        chunks = list(chunks)
        live_ids = sorted(
            self._live, key=lambda l: (self._live[l].position, self._live[l].part_index, l)
        )
        free = set(live_ids) 
        new_to_old = {}       
        by_key = {self._key[l]: l for l in live_ids}

        def take(i, lid):
            new_to_old[i] = lid
            free.discard(lid)

        
        for i, c in enumerate(chunks):
            lid = by_key.get(c.key)
            if lid in free and self._live[lid].content_hash == c.content_hash:
                take(i, lid)

        
        by_hash = {}
        for l in live_ids:
            if l in free:
                by_hash.setdefault(self._live[l].content_hash, []).append(l)
        for i, c in enumerate(chunks):
            if i in new_to_old:
                continue
            cands = by_hash.get(c.content_hash)
            if cands:
                take(i, cands.pop(0))

        
        for i, c in enumerate(chunks):
            if i in new_to_old:
                continue
            lid = by_key.get(c.key)
            if lid in free:
                take(i, lid)

        
        rest_new = [i for i in range(len(chunks)) if i not in new_to_old]
        rest_old = [l for l in live_ids if l in free]
        if rest_new and rest_old and len(rest_new) * len(rest_old) <= FUZZY_MAX_PAIRS:
            scored = []
            for i in rest_new:
                for l in rest_old:
                    r = _ratio(self._live[l].text, chunks[i].text)
                    if r >= FUZZY_MIN_RATIO:
                        scored.append((-r, i, l))
            scored.sort()
            for _, i, l in scored:
                if i not in new_to_old and l in free:
                    take(i, l)

        
        matched_key = {}
        for i, c in enumerate(chunks):
            lid = new_to_old.get(i)
            if lid is None:
                continue
            matched_key[c.key] = lid
            v = self._live[lid]
            if _state(v) != (c.content_hash, c.section_path, c.part_index, c.position):
                v.to_rev = rev_id
                self._open(lid, c, rev_id)
            else:
                self._key[lid] = c.key  # e.g. only the occurrence number changed

        
        for lid in sorted(free):
            self._live.pop(lid).to_rev = rev_id
            self._key.pop(lid)

        
        for i, c in enumerate(chunks):
            if i in new_to_old:
                continue
            origin, related = "new", []
            if c.part_index > 0:
                sibling = matched_key.get((c.section_path, c.occurrence, 0))
                if sibling is not None:
                    origin, related = "split", [sibling]
            self._open(self._new_lineage(rev_id, origin, related), c, rev_id)
