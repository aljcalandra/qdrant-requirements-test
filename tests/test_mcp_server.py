import json

import pytest
from conftest import ORIGINS, req, spec
from mcp import Client

from reqtrack import sync
from reqtrack.mcp_server import build

pytestmark = [pytest.mark.mcp, pytest.mark.store, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def server(s, log):
    old_test = spec("def test_password_login(): pass")
    sync.run(s, log, [req("password login"), old_test], ORIGINS, now=1_790_000_000)
    sync.run(s, log, [req("passkey login"), old_test], ORIGINS, now=1_790_100_000)
    return build(s, log)


async def call(server, tool, **args):
    async with Client(server, raise_exceptions=True) as client:
        res = await client.call_tool(tool, args)
        assert not res.is_error, res.content
        if res.structured_content is None:
            return json.loads(res.content[0].text)
        return res.structured_content["result"]


async def test_lists_read_only_tools(server):
    async with Client(server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
    assert names == {"search", "show", "history", "diff", "trace", "changes"}


async def test_search_by_kind(server):
    hits = await call(server, "search", query="login", kinds=["requirement"])
    assert [(h["key"], h["version"]) for h in hits] == [("confluence:1", 2)]


async def test_search_all_versions(server):
    hits = await call(server, "search", query="login", kinds=["requirement"], all_versions=True)
    assert sorted(h["version"] for h in hits) == [1, 2]


async def test_search_as_of(server):
    hits = await call(server, "search", query="login", kinds=["requirement"], as_of="2026-09-22")
    assert [h["version"] for h in hits] == [1]


async def test_show_and_diff(server):
    doc = await call(server, "show", key="confluence:1", version=1)
    assert doc["content"] == "password login"
    patch = await call(server, "diff", key="confluence:1", a=1, b=2)
    assert "-password login" in patch and "+passkey login" in patch


async def test_history_and_changes(server):
    events = await call(server, "history", key="confluence:1")
    assert [e["change"] for e in events] == ["added", "modified"]
    tests = await call(server, "changes", kinds=["test"])
    assert [e["key"] for e in tests] == ["file:tests/test_login.py"]


async def test_trace(server):
    hits = await call(server, "trace", key="confluence:1")
    assert [(h["key"], h["status"]) for h in hits] == [("file:tests/test_login.py", "review")]


@pytest.mark.parametrize(
    "tool, args, message",
    [
        ("show", {"key": "confluence:999"}, "unknown key: confluence:999"),
        ("show", {"key": "confluence:1", "version": 9}, "no version 9 of confluence:1"),
        ("diff", {"key": "confluence:1", "a": 1, "b": 9}, "no version 9 of confluence:1"),
        ("trace", {"key": "confluence:999"}, "unknown key: confluence:999"),
    ],
)
async def test_unknown_key_or_version_is_an_error(server, tool, args, message):
    async with Client(server) as client:
        res = await client.call_tool(tool, args)
    assert res.is_error
    assert message in res.content[0].text
