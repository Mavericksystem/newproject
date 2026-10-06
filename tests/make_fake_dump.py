import hashlib, sys

NS = "http://www.mediawiki.org/xml/export-0.11/"

def rev(rid, parent, ts, user, text, comment="", minor=False, ip=False, del_text=False, del_contrib=False):
    sha = hashlib.sha1(text.encode()).hexdigest()
    c = ('<contributor deleted="deleted" />' if del_contrib else
         f"<contributor><ip>1.2.3.{rid % 250}</ip></contributor>" if ip else
         f"<contributor><username>{user}</username><id>{rid}</id></contributor>")
    t = (f'<text bytes="{len(text.encode())}" deleted="deleted" />' if del_text
         else f'<text bytes="{len(text.encode())}" xml:space="preserve">{text}</text>')
    cm = f"<comment>{comment}</comment>" if comment else ""
    return (f"<revision><id>{rid}</id>{'<parentid>%d</parentid>' % parent if parent else ''}"
            f"<timestamp>{ts}</timestamp>{c}{'<minor />' if minor else ''}{cm}"
            f"<model>wikitext</model><format>text/x-wiki</format>{t}<sha1>{sha}</sha1></revision>")

good = "Intro with a [[link]] and {{Infobox person|name=X}}. " * 20
vandal = "VANDALISM"
revs_a = [
    rev(1, 0, "2004-09-21T10:00:00Z", "Alice", good),
    rev(2, 1, "2004-09-22T10:00:00Z", "Bob", good + " more text"),
    rev(3, 2, "2004-09-23T10:00:00Z", "x", vandal, ip=True),                # vandal
    rev(4, 3, "2004-09-23T10:05:00Z", "ClueBot NG", good + " more text", comment="Reverting vandalism"),  # revert to rev 2
    rev(5, 4, "2005-01-01T00:00:00Z", "Carol", good + " more text", minor=True),   # null edit
    rev(6, 5, "2005-02-01T00:00:00Z", "Dave", "", comment="blank"),                 # blanked
    rev(7, 6, "2005-02-01T00:10:00Z", "Eve", good + " more text", comment="rv blanking"),  # revert to 5/4/2
    rev(8, 7, "2006-01-01T00:00:00Z", "gone", "secret", del_text=True, del_contrib=True),
    rev(9, 8, "2006-02-01T00:00:00Z", "Frank", good + " final"),
]