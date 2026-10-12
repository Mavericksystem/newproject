import re
import sys
from dataclasses import dataclass

import mwparserfromhell

# Bump the suffix whenever section splitting or plain-text rules change.
PARSER_VERSION = f"mwparserfromhell-{mwparserfromhell.__version__}/sections-2"
PATH_SEP = " > "

# Links that are navigation/media, not prose. ([[:Category:X]] with a leading colon is a
# visible link and is kept.)
_NON_PROSE_LINK_PREFIXES = ("category:", "file:", "image:")

# Blocks in which "== x ==" must not count as a heading. An unclosed comment runs to the
# end of the text (as MediaWiki does). A self-closing tag such as <nowiki/> is not a block.
_MASKED = re.compile(
    r"<!--.*?(?:-->|\Z)"
    r"|<(nowiki|pre|source|syntaxhighlight|math)\b[^>]*(?<!/)>.*?</\1\s*>",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class Section:
    position: int    # 0-based order among emitted (non-empty) sections
    level: int       # 0 = lead, otherwise the heading level (2 for "== x ==")
    heading: str     # '' for the lead
    path: str        # 'History > Early use'; '' for the lead
    occurrence: int  # 0-based count of earlier headings with the same path
    wikitext: str    # raw body wikitext, heading line excluded, stripped


def _mask(wikitext):
    """Same-length copy of the text with the masked blocks replaced by spaces
    (newlines kept, so line offsets stay identical)."""
    return _MASKED.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), wikitext)


def _heading(line):
    """Return (level, raw_title) if the (masked) line is a heading, else None."""
    s = line.rstrip()
    if len(s) < 3 or s[0] != "=" or s[-1] != "=":
        return None
    lead = len(s) - len(s.lstrip("="))
    trail = len(s) - len(s.rstrip("="))
    if lead == len(s):  # only "=" characters
        return None
    level = min(lead, trail, 6)
    title = s[level : len(s) - level].strip()
    if not title:
        return None
    return level, title


def _clean_title(raw):
    """Strip wiki markup from a heading title ('[[X|y]]' -> 'y', "''x''" -> 'x')."""
    try:
        text = mwparserfromhell.parse(raw).strip_code().strip()
    except Exception:
        text = ""
    return " ".join((text or raw).split())


def split_sections(wikitext):
    """Split wikitext into flat sections. Sections with an empty body are skipped."""
    masked = _mask(wikitext)

    heads = []  # (line_start, line_end, level, title)
    pos = 0
    for line in masked.split("\n"):
        end = pos + len(line)
        h = _heading(line)
        if h:
            heads.append((pos, end, h[0], _clean_title(h[1])))
        pos = end + 1

    out = []

    def emit(level, heading, path, occ, start, end):
        body = wikitext[start:end].strip()
        if body:
            out.append(Section(len(out), level, heading, path, occ, body))

    emit(0, "", "", 0, 0, heads[0][0] if heads else len(wikitext))

    stack = []  # (level, title) of the currently open headings
    seen = {}   # path -> how many times it has appeared
    for i, (_start, line_end, level, title) in enumerate(heads):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        path = PATH_SEP.join(t for _, t in stack)
        occ = seen.get(path, 0)
        seen[path] = occ + 1
        body_end = heads[i + 1][0] if i + 1 < len(heads) else len(wikitext)
        emit(level, title, path, occ, line_end, body_end)
    return out


def to_plain(wikitext):
    """Wikitext -> plain prose. Templates, <ref> contents and comments are dropped,
    as are Category/File/Image links. Known limit: table markup ({| ... |}) is not
    stripped."""
    code = mwparserfromhell.parse(wikitext)
    for link in code.filter_wikilinks():
        if str(link.title).strip().lower().startswith(_NON_PROSE_LINK_PREFIXES):
            try:
                code.remove(link)
            except ValueError:
                pass  # already removed together with an enclosing node
    text = code.strip_code(normalize=True, collapse=True)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def main(argv):
    """Hand-check helper:
        python src/knowledge/parse_wikitext.py rev.txt          # section outline
        python src/knowledge/parse_wikitext.py rev.txt 3        # plain text of section 3
    """
    if len(argv) < 2:
        raise SystemExit("usage: parse_wikitext.py <wikitext-file> [section-position]")
    with open(argv[1], encoding="utf-8-sig") as f:
        sections = split_sections(f.read())
    if len(argv) >= 3:
        s = sections[int(argv[2])]
        print(f"[{s.position}] {s.path or '(lead)'}  occurrence={s.occurrence}\n")
        print(to_plain(s.wikitext))
        return
    print(f"parser: {PARSER_VERSION}")
    print(f"{len(sections)} sections\n")
    for s in sections:
        print(f"{s.position:3}  L{s.level}  occ{s.occurrence}  {len(s.wikitext):7}B  {s.path or '(lead)'}")


if __name__ == "__main__":
    main(sys.argv)