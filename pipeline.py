import bz2
from lxml import etree

FILE = "enwiki-2026-09-01-p1001122p1004186.xml.bz2"

with bz2.open(FILE, "rb") as f:
    for event, elem in etree.iterparse(
        f,
        events=("end",),
        tag="{*}page"
    ):

        # Process one page at a time
        title = elem.findtext("./{*}title")
        page_id = elem.findtext("./{*}id")

        for revision in elem.findall("./{*}revision"):
            revision_id = revision.findtext("./{*}id")
            timestamp = revision.findtext("./{*}timestamp")
            comment = revision.findtext("./{*}comment")
            text = revision.findtext("./{*}text")

            # send to your normalization/storage pipeline
            print(page_id, title, revision_id, timestamp)