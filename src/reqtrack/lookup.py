import difflib
from datetime import datetime

from reqtrack import changelog, store

TESTS = ["test_plan", "test"]


def show(s, events, key, version=None):
    if version is None:
        version = known(changelog.latest(events), key)["version"]
    return found(store.get_version(s, key, version), key, version)


def known(events_by_key, key):
    if key not in events_by_key:
        raise LookupError(f"unknown key: {key}")
    return events_by_key[key]


def found(doc, key, version):
    if doc is None:
        raise LookupError(f"no version {version} of {key}")
    return doc


def diff(s, key, a, b):
    old = found(store.get_version(s, key, a), key, a)
    new = found(store.get_version(s, key, b), key, b)
    lines = difflib.unified_diff(
        old["content"].splitlines(),
        new["content"].splitlines(),
        fromfile=f"{key} v{a}",
        tofile=f"{key} v{b}",
        lineterm="",
    )
    return "\n".join(lines)


def search_as_of(s, events, q, at, kinds=None, limit=10):
    valid = changelog.as_of(events, at)
    hits = store.search(s, q, kinds, history=True, before=at, limit=limit * 4)
    keep = [h for h in hits if h["key"] in valid and valid[h["key"]]["version"] == h["version"]]
    return keep[:limit]


def trace(s, events, key, limit=10):
    """Tests and test plans closest to a requirement, flagged when older than it."""
    live = changelog.live(events)
    req = known(live, key)
    doc = found(store.get_version(s, key, req["version"]), key, req["version"])
    hits = store.search(s, doc["title"] + "\n" + doc["content"][:2000], TESTS, limit=limit)
    for h in hits:
        h["status"] = "review" if live[h["key"]]["at"] < req["at"] else "ok"
    return hits


def to_epoch(text):
    return int(datetime.fromisoformat(text).timestamp())
