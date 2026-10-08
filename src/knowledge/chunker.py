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


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hard_split(piece, max_chars):
    """Cut one over-long piece at word boundaries; slice a single over-long word."""
    if len(piece) <= max_chars:
        return [piece]
    out, cur = [], ""
    for word in piece.split():
        while len(word) > max_chars:
            if cur:
                out.append(cur)
                cur = ""
            out.append(word[:max_chars])
            word = word[max_chars:]
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur += " " + word
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def _units(text, max_chars):
    """Yield (separator_before, unit) pairs, each unit at most max_chars long."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for pi, para in enumerate(paras):
        lead_sep = "\n\n" if pi else ""
        if len(para) <= max_chars:
            yield lead_sep, para
            continue
        bits = _BOUNDARY.split(para)  # [piece, sep, piece, sep, ...]
        sep = lead_sep
        for i in range(0, len(bits), 2):
            if i:
                sep = bits[i - 1]
            if not bits[i]:
                continue
            for j, sub in enumerate(_hard_split(bits[i], max_chars)):
                yield (sep if j == 0 else " "), sub


def split_text(text, max_chars=MAX_CHARS):
    """Split plain text into parts of at most max_chars. Short text comes back unchanged."""
    if len(text) <= max_chars:
        return [text]
    parts, cur = [], ""
    for sep, unit in _units(text, max_chars):
        if not cur:
            cur = unit
        elif len(cur) + len(sep) + len(unit) <= max_chars:
            cur += sep + unit
        else:
            parts.append(cur)
            cur = unit
    if cur:
        parts.append(cur)
    return parts


def _plain(wikitext, cache):
    if cache is None:
        return to_plain(wikitext)
    key = sha256_text(wikitext)
    if key not in cache:
        cache[key] = to_plain(wikitext)
    return cache[key]


def chunk_sections(sections, max_chars=MAX_CHARS, plain_cache=None):
    """Turn Sections into Chunks. Sections whose plain text is empty (only templates,
    refs or categories) produce no chunk. Pass a dict as plain_cache to avoid re-converting
    identical section wikitext across revisions."""
    chunks = []
    for s in sections:
        plain = _plain(s.wikitext, plain_cache)
        if not plain:
            continue
        for part_index, text in enumerate(split_text(plain, max_chars)):
            chunks.append(
                Chunk(
                    position=len(chunks),
                    section_path=s.path,
                    occurrence=s.occurrence,
                    part_index=part_index,
                    text=text,
                    content_hash=sha256_text(text),
                )
            )
    return chunks

