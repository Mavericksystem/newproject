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

