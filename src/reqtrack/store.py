"""Vector store. Two collections:
history: every version of every document, append-only.
current: the latest live version of each document.

Points use the mcp-server-qdrant layout (named vector "fast-<model>",
payload "document" + "metadata") so that server can search them.
"""

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from reqtrack.doc import version_id

CHUNK = 800
FIELDS = ["key", "origin", "kind", "title", "url", "version", "hash", "change", "at"]


@dataclass
class Store:
    client: object
    history: str
    current: str
    embed: object
    vector: str


def connect(cfg, embed):
    if cfg.store_url:
        client = QdrantClient(url=cfg.store_url)
    else:
        client = QdrantClient(path=cfg.store_path)
    return open_store(client, cfg.collection, embed, vector_name(cfg.model))


def vector_name(model):
    return "fast-" + model.split("/")[-1].lower()


def open_store(client, name, embed, vector="fast-test"):
    s = Store(client, name + "_history", name + "_current", embed, vector)
    size = len(embed(["probe"])[0])
    for coll in (s.history, s.current):
        if not client.collection_exists(coll):
            params = models.VectorParams(size=size, distance=models.Distance.COSINE)
            client.create_collection(coll, vectors_config={vector: params})
    return s


def chunks(text):
    out, buf = [], ""
    for para in text.split("\n"):
        for i in range(0, max(len(para), 1), CHUNK):
            piece = para[i : i + CHUNK]
            if buf and len(buf) + len(piece) > CHUNK:
                out.append(buf)
                buf = ""
            buf = buf + "\n" + piece if buf else piece
    if buf.strip():
        out.append(buf)
    return out or [""]


def points(s, doc, event, prefix):
    texts = [doc.title + "\n" + p for p in chunks(doc.content)]
    out = []
    for i, (text, vec) in enumerate(zip(texts, s.embed(texts))):
        payload = payload_for(doc, event, i, text)
        pid = point_id(prefix, event["key"], event["version"], i)
        out.append(models.PointStruct(id=pid, vector={s.vector: vec}, payload=payload))
    return out


def payload_for(doc, event, i, text):
    meta = {f: event[f] for f in FIELDS}
    meta["vid"] = version_id(event["key"], event["version"])
    meta["chunk"] = i
    meta["source_version"] = doc.source_version
    meta["source_updated"] = doc.source_updated
    p = {"document": text, "metadata": meta}
    if i == 0:
        p["content"] = doc.content
    return p


def point_id(prefix, key, version, chunk):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{prefix}:{key}:{version}:{chunk}"))


def write(s, doc, event):
    s.client.upsert(s.history, points=points(s, doc, event, "history"))
    delete_key(s, s.current, event["key"])
    s.client.upsert(s.current, points=points(s, doc, event, "current"))


def remove(s, event):
    text = "Removed: " + event["title"]
    meta = {f: event[f] for f in FIELDS}
    meta.update(vid=version_id(event["key"], event["version"]), chunk=0)
    payload = {"document": text, "metadata": meta, "content": ""}
    vec = s.embed([text])[0]
    pid = point_id("history", event["key"], event["version"], 0)
    point = models.PointStruct(id=pid, vector={s.vector: vec}, payload=payload)
    s.client.upsert(s.history, points=[point])
    delete_key(s, s.current, event["key"])


def delete_key(s, coll, key):
    selector = models.FilterSelector(filter=match_filter(key=key))
    s.client.delete(coll, points_selector=selector)


def match_filter(**fields):
    return models.Filter(must=[match(k, v) for k, v in fields.items()])


def match(field, value):
    return models.FieldCondition(key="metadata." + field, match=models.MatchValue(value=value))


def search(s, q, kinds=None, history=False, before=None, limit=10):
    coll = s.history if history else s.current
    flt = search_filter(kinds, before)
    vec = s.embed([q])[0]
    res = s.client.query_points(
        coll, query=vec, using=s.vector, query_filter=flt, limit=limit * 4, with_payload=True
    )
    return best_per_version(res.points, limit)


def search_filter(kinds, before):
    must = []
    if kinds:
        any_kind = models.MatchAny(any=list(kinds))
        must.append(models.FieldCondition(key="metadata.kind", match=any_kind))
    if before is not None:
        must.append(models.FieldCondition(key="metadata.at", range=models.Range(lte=before)))
    return models.Filter(must=must, must_not=[match("change", "removed")])


def best_per_version(found, limit):
    hits = {}
    for p in found:
        meta = p.payload["metadata"]
        if meta["vid"] not in hits:
            hit = {f: meta[f] for f in FIELDS}
            hit["score"] = p.score
            hit["text"] = p.payload["document"]
            hits[meta["vid"]] = hit
    return list(hits.values())[:limit]


def get_version(s, key, version):
    flt = match_filter(key=key, version=version, chunk=0)
    found, _ = s.client.scroll(s.history, scroll_filter=flt, limit=1, with_payload=True)
    if not found:
        return None
    p = found[0].payload
    return dict(p["metadata"], content=p["content"])
