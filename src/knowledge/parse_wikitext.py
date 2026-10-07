import sys
from dataclasses import dataclass

import mwparserfromhell
from mwparserfromhell.nodes import Heading

PARSER_VERSION = f"mwparserfromhell-{mwparserfromhell.__version__}/sections-1"
PATH_SEP = " > "


_NON_PROSE_LINK_PREFIXES = ("category:", "file:", "image:")


@dataclass(frozen=True)
class Section:
    position: int    
    level: int      
    heading: str     
    path: str        
    occurrence: int  
    wikitext: str    


def _heading_title(node):
    title = node.title.strip_code().strip()
    if not title:
        title = str(node.title).strip()
    return " ".join(title.split())


def split_sections(wikitext):
    """Split wikitext into flat sections. Sections with an empty body are skipped."""
    code = mwparserfromhell.parse(wikitext)

    out = []
    buf = []
    stack = []  
    seen = {}   
    cur = {"level": 0, "heading": "", "path": "", "occ": 0}

    def emit():
        body = "".join(buf).strip()
        buf.clear()
        if body:
            out.append(
                Section(
                    position=len(out),
                    level=cur["level"],
                    heading=cur["heading"],
                    path=cur["path"],
                    occurrence=cur["occ"],
                    wikitext=body,
                )
            )

    for node in code.nodes:
        if isinstance(node, Heading):
            emit()
            title = _heading_title(node)
            while stack and stack[-1][0] >= node.level:
                stack.pop()
            stack.append((node.level, title))
            path = PATH_SEP.join(t for _, t in stack)
            occ = seen.get(path, 0)
            seen[path] = occ + 1
            cur.update(level=node.level, heading=title, path=path, occ=occ)
        else:
            buf.append(str(node))
    emit()
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