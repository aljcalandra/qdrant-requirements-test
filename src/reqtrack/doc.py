import hashlib
from dataclasses import dataclass


@dataclass
class Doc:
    """One source document as read from Confluence or disk."""

    key: str
    origin: str
    kind: str
    title: str
    url: str
    content: str
    source_version: str = ""
    source_updated: str = ""


def content_hash(doc):
    text = doc.title + "\n" + doc.content
    return hashlib.sha256(text.encode()).hexdigest()


def doc_id(key):
    return hashlib.sha1(key.encode()).hexdigest()[:20]


def version_id(key, version):
    return f"{doc_id(key)}-v{version}"
