import bz2
from lxml import etree

FILE = "enwiki-2026-09-01-p1001122p1004186.xml.bz2"

with bz2.open(FILE, "rb") as f:
    for event, elem in etree.iterparse(
        f,
        events=("end",),
        tag="{*}page"
    ):