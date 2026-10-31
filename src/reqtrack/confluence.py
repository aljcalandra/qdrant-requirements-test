import os
from html.parser import HTMLParser

import requests

from reqtrack.doc import Doc

BLOCKS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre"}
CELLS = {"td", "th"}
SKIP = {"ac:parameter", "style", "script"}


def session():
    """Cloud: CONFLUENCE_EMAIL + CONFLUENCE_TOKEN. Data Center: CONFLUENCE_PAT."""
    s = requests.Session()
    pat = os.environ.get("CONFLUENCE_PAT")
    if pat:
        s.headers["Authorization"] = "Bearer " + pat
    else:
        s.auth = (os.environ["CONFLUENCE_EMAIL"], os.environ["CONFLUENCE_TOKEN"])
    return s


def scan(s, base_url, space, labels):
    return [to_doc(p, base_url, space, labels) for p in pages(s, base_url, space.key)]


def pages(s, base_url, space_key):
    url = base_url + "/rest/api/content"
    params = {
        "spaceKey": space_key,
        "type": "page",
        "expand": "body.storage,version,metadata.labels",
        "limit": 50,
    }
    while url:
        r = s.get(url, params=params, timeout=30)
        r.raise_for_status()
        body = r.json()
        yield from body.get("results", [])
        nxt = body.get("_links", {}).get("next")
        url = base_url + nxt if nxt else None
        params = None


def to_doc(page, base_url, space, labels):
    return Doc(
        key="confluence:" + page["id"],
        origin="confluence:" + space.key,
        kind=kind(page, space, labels),
        title=page["title"],
        url=base_url + page["_links"]["webui"],
        content=to_text(page["body"]["storage"]["value"]),
        source_version=str(page["version"]["number"]),
        source_updated=page["version"].get("when", ""),
    )


def kind(page, space, labels):
    names = [lb["name"] for lb in page.get("metadata", {}).get("labels", {}).get("results", [])]
    for name in names:
        if name in labels:
            return labels[name]
    return space.kind


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif tag in BLOCKS:
            self.parts.append("\n")
        elif tag in CELLS:
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip -= 1
        elif tag in BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def to_text(html):
    p = TextParser()
    p.feed(html)
    lines = [" ".join(line.split()) for line in "".join(p.parts).splitlines()]
    return "\n".join(line for line in lines if line)
