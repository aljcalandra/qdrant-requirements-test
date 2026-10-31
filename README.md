# reqtrack

Search over requirements, test plans, and tests, with every version tracked.

reqtrack reads Confluence pages and local files into Qdrant. Each change is stored as a
new version, and old versions stay available for lookup. A change log records every
change so other tools can follow how requirements and their tests change.

## Getting started

### 1. Start Qdrant

Download a build from the [Qdrant releases](https://github.com/qdrant/qdrant/releases)
and run it:

```sh
tar xzf qdrant-aarch64-apple-darwin.tar.gz
./qdrant
```

### 2. Install and configure

```sh
uv sync
cp reqtrack.example.yaml reqtrack.yaml
```

Edit `reqtrack.yaml` to list your Confluence spaces and folders, then set credentials:

- Confluence Cloud: `CONFLUENCE_EMAIL` and `CONFLUENCE_TOKEN`
- Confluence Data Center: `CONFLUENCE_PAT`

### 3. Load documents

```sh
uv run reqtrack sync
```

Run it again whenever sources change.

### 4. Start the MCP servers

```sh
REQTRACK_CONFIG=reqtrack.yaml uv run reqtrack-mcp
```

```sh
QDRANT_URL=http://localhost:6333 \
COLLECTION_NAME=requirements_current \
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
QDRANT_READ_ONLY=true \
uvx mcp-server-qdrant
```

In Claude Code, `.mcp.json` starts both for you from the repo root.

## MCP tools

| Tool | Does |
|---|---|
| `search` | search by meaning, optionally by kind, across all versions, or as of a date |
| `show` | full content of a version |
| `history` | every change to a document |
| `diff` | differences between two versions |
| `trace` | tests and test plans for a requirement |
| `changes` | the change log, by date and kind |

## Commands

```sh
reqtrack sync
reqtrack search "account lockout"
reqtrack search "account lockout" --all-versions
reqtrack search "account lockout" --as-of 2026-09-01
reqtrack search "lockout" --kind test --kind test_plan
reqtrack history confluence:12345
reqtrack show confluence:12345 --version 2
reqtrack diff confluence:12345 1 2
reqtrack trace confluence:12345
reqtrack changes --since 2026-10-01 --kind requirement
```

Add `--json` before the command for JSON output: `reqtrack --json changes`.

- Kinds: `requirement`, `test_plan`, `test`
- Keys: `confluence:<page id>` or `file:<folder>/<path>`
- `trace` marks a test or test plan `review` when it last changed before the requirement

## Change log

Each line of `data/changes.jsonl` is one change:

```json
{"key": "confluence:12345", "origin": "confluence:REQ", "kind": "requirement",
 "title": "Login", "url": "https://…", "version": 2, "hash": "…",
 "change": "modified", "at": 1793400000}
```

`change` is `added`, `modified`, `removed` or `readded`. `at` is Unix seconds.

## Tests

```sh
uv run pytest
uv run pytest -m unit
uv run pytest -m store
uv run pytest -m confluence
uv run pytest -m mcp
```
