"""Append-only change log. One JSON event per line, never rewritten."""

import json
import os


def read(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def append(path, events):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def latest(events):
    """Latest event per key, removed keys included."""
    out = {}
    for e in events:
        out[e["key"]] = e
    return out


def live(events):
    """Latest event per key, removed keys left out."""
    return {k: e for k, e in latest(events).items() if e["change"] != "removed"}


def for_key(events, key):
    return [e for e in events if e["key"] == key]


def since(events, at):
    return [e for e in events if e["at"] >= at]


def as_of(events, at):
    """Version of each key that was live at time `at`."""
    return live([e for e in events if e["at"] <= at])
