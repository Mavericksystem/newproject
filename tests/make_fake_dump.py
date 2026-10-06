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