"""Read-only MCP server over reqtrack's store and change log."""

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from reqtrack import changelog, config, embed, lookup, store

INSTRUCTIONS = """Requirements, test plans and tests, with every version kept.
Document keys look like confluence:<page id> or file:<path>.
Kinds: requirement, test_plan, test.
Dates are ISO, e.g. 2026-10-01 or 2026-10-01T14:00."""


def build(s, log_path):
    server = MCPServer("reqtrack", instructions=INSTRUCTIONS)

    def events():
        return changelog.read(log_path)

    @server.tool()
    def search(
        query: str,
        kinds: list[str] | None = None,
        all_versions: bool = False,
        as_of: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Semantic search. Latest versions by default; all_versions searches every
        version; as_of searches the versions that were live at that date."""
        if as_of:
            return lookup.search_as_of(s, events(), query, lookup.to_epoch(as_of), kinds, limit)
        return store.search(s, query, kinds, history=all_versions, limit=limit)

    @server.tool()
    def show(key: str, version: int | None = None) -> dict:
        """Full content and metadata of one version (latest when version is omitted)."""
        return check(lookup.show, s, events(), key, version)

    @server.tool()
    def history(key: str) -> list[dict]:
        """Every change event for one document, oldest first."""
        return changelog.for_key(events(), key)

    @server.tool()
    def diff(key: str, a: int, b: int) -> str:
        """Unified diff between two versions of one document."""
        return check(lookup.diff, s, key, a, b)

    @server.tool()
    def trace(key: str, limit: int = 10) -> list[dict]:
        """Tests and test plans closest to a requirement. status is "review" when the
        test or test plan last changed before the requirement did, else "ok"."""
        return check(lookup.trace, s, events(), key, limit)

    @server.tool()
    def changes(since: str | None = None, kinds: list[str] | None = None) -> list[dict]:
        """Change log events, optionally since a date and for some kinds."""
        found = changelog.since(events(), lookup.to_epoch(since)) if since else events()
        return [e for e in found if not kinds or e["kind"] in kinds]

    return server


def check(fn, *args):
    """Report a missing key or version to the client as a plain tool error."""
    try:
        return fn(*args)
    except LookupError as e:
        raise ToolError(str(e)) from None


def main():
    cfg = config.load(os.environ.get("REQTRACK_CONFIG", "reqtrack.yaml"))
    s = store.connect(cfg, embed.local(cfg.model))
    build(s, cfg.log).run()


if __name__ == "__main__":
    main()
