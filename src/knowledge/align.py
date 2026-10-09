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
