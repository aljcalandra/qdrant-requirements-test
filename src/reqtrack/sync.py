import time

from reqtrack import changelog, store
from reqtrack.doc import content_hash


def plan(events, docs, origins, now):
    """Return (event, doc) pairs for what changed. doc is None for removals."""
    last = changelog.latest(events)
    out = []
    seen = set()
    for doc in docs:
        seen.add(doc.key)
        prev = last.get(doc.key)
        change = change_for(prev, content_hash(doc))
        if change:
            out.append((event_for(doc, prev, change, now), doc))
    for key, prev in last.items():
        if prev["origin"] in origins and key not in seen and prev["change"] != "removed":
            out.append((removal(prev, now), None))
    return out


def change_for(prev, h):
    if prev is None:
        return "added"
    if prev["change"] == "removed":
        return "readded"
    if prev["hash"] != h:
        return "modified"
    return None


def event_for(doc, prev, change, now):
    return {
        "key": doc.key,
        "origin": doc.origin,
        "kind": doc.kind,
        "title": doc.title,
        "url": doc.url,
        "version": prev["version"] + 1 if prev else 1,
        "hash": content_hash(doc),
        "change": change,
        "at": now,
    }


def removal(prev, now):
    return dict(prev, version=prev["version"] + 1, change="removed", at=now)


def run(s, log_path, docs, origins, now=None):
    now = now or int(time.time())
    events = changelog.read(log_path)
    todo = plan(events, docs, origins, now)
    for event, doc in todo:
        if doc is None:
            store.remove(s, event)
        else:
            store.write(s, doc, event)
        changelog.append(log_path, [event])
    return [e for e, _ in todo]
