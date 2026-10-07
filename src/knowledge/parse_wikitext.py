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

