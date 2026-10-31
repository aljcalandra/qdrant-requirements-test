import glob
import os

from reqtrack.doc import Doc


def scan(src):
    paths = glob.glob(os.path.join(src.path, src.glob), recursive=True)
    return [read(src, p) for p in sorted(paths) if os.path.isfile(p)]


def read(src, path):
    rel = os.path.relpath(path, os.path.dirname(src.path))
    with open(path, errors="replace") as f:
        content = f.read()
    return Doc(
        key="file:" + rel,
        origin=origin(src),
        kind=src.kind,
        title=os.path.basename(path),
        url=rel,
        content=content,
    )


def origin(src):
    return "files:" + os.path.basename(src.path.rstrip("/"))
