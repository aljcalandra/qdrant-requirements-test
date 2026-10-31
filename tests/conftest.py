import re

import pytest
from qdrant_client import QdrantClient

from reqtrack import store
from reqtrack.doc import Doc

ORIGINS = {"confluence:REQ", "files:tests"}

# One vector dimension per word, plus one constant dimension so no vector is all zeros.
VOCAB = "login password passkey users test def pass rule system thing removed".split()


def fake_embed(texts):
    out = []
    for text in texts:
        words = re.findall("[a-z]+", text.lower())
        out.append([1.0] + [float(words.count(w)) for w in VOCAB])
    return out


def req(content, title="Login"):
    return Doc("confluence:1", "confluence:REQ", "requirement", title, "u", content)


def spec(content):
    return Doc("file:tests/test_login.py", "files:tests", "test", "test_login.py", "p", content)


@pytest.fixture
def s():
    return store.open_store(QdrantClient(":memory:"), "t", fake_embed)


@pytest.fixture
def log(tmp_path):
    return str(tmp_path / "log.jsonl")
