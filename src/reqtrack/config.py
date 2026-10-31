import os
from dataclasses import dataclass, field

import yaml


@dataclass
class Space:
    key: str
    kind: str = "requirement"


@dataclass
class FileSource:
    path: str
    kind: str
    glob: str = "**/*"


@dataclass
class Config:
    store_path: str = "data/qdrant"
    store_url: str = ""
    collection: str = "requirements"
    model: str = "BAAI/bge-small-en-v1.5"
    log: str = "data/changes.jsonl"
    confluence_url: str = ""
    spaces: list = field(default_factory=list)
    labels: dict = field(default_factory=dict)
    files: list = field(default_factory=list)


def load(path):
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    root = os.path.dirname(os.path.abspath(path))
    store = raw.get("store", {})
    confluence = raw.get("confluence", {})
    cfg = Config()
    cfg.store_path = os.path.join(root, store.get("path", cfg.store_path))
    cfg.store_url = store.get("url", "")
    cfg.collection = store.get("collection", cfg.collection)
    cfg.model = store.get("model", cfg.model)
    cfg.log = os.path.join(root, raw.get("log", cfg.log))
    cfg.confluence_url = confluence.get("base_url", "").rstrip("/")
    cfg.spaces = [Space(**s) for s in confluence.get("spaces", [])]
    cfg.labels = confluence.get("labels", {})
    cfg.files = [file_source(f, root) for f in raw.get("files", [])]
    return cfg


def file_source(raw, root):
    src = FileSource(**raw)
    src.path = os.path.join(root, src.path)
    return src
