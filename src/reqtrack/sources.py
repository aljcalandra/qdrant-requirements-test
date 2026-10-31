from reqtrack import confluence, files


def collect(cfg):
    """Read every configured source. Returns (docs, origins scanned)."""
    docs, origins = [], set()
    if cfg.spaces:
        s = confluence.session()
        for space in cfg.spaces:
            docs += confluence.scan(s, cfg.confluence_url, space, cfg.labels)
            origins.add("confluence:" + space.key)
    for src in cfg.files:
        docs += files.scan(src)
        origins.add(files.origin(src))
    return docs, origins
