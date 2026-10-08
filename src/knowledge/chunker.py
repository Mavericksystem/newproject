import hashlib
import re
import sys
from dataclasses import dataclass

from parse_wikitext import PARSER_VERSION, split_sections, to_plain

MAX_CHARS = 3000  # roughly 600-750 tokens of English prose

CHUNKER_VERSION = f"chunker-1/max{MAX_CHARS}"


_BOUNDARY = re.compile(r"((?<=[.!?])[ \t]+|\n)")


@dataclass(frozen=True)
class Chunk:
    position: int      # 0-based order across the whole page
    section_path: str  # '' for the lead
    occurrence: int    # distinguishes duplicate headings (see parse_wikitext)
    part_index: int    # 0 unless the section was split
    text: str          # plain text
    content_hash: str  # sha256 hex of text (UTF-8)

    @property
    def key(self):
        return (self.section_path, self.occurrence, self.part_index)

