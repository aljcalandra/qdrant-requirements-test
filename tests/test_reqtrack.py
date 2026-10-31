import pytest
from conftest import ORIGINS, fake_embed, req, spec

from reqtrack import changelog, confluence, lookup, store, sync
from reqtrack.config import Space


def changes(log):
    return [(e["version"], e["change"]) for e in changelog.read(log)]


@pytest.mark.unit
def test_fake_embed_is_fixed():
    assert fake_embed(["Login with a password"]) == [[1.0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]]


@pytest.mark.unit
@pytest.mark.parametrize(
    "prev, h, expected",
    [
        (None, "a", "added"),
        ({"change": "added", "hash": "a"}, "a", None),
        ({"change": "added", "hash": "a"}, "b", "modified"),
        ({"change": "removed", "hash": "a"}, "a", "readded"),
    ],
)
def test_change_for(prev, h, expected):
    assert sync.change_for(prev, h) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "text, count",
    [
        ("", 1),
        ("short", 1),
        ("x" * (store.CHUNK + 1), 2),
        ("\n".join(["y" * 500] * 4), 4),
    ],
)
def test_chunks(text, count):
    assert len(store.chunks(text)) == count


@pytest.mark.store
def test_versions_are_kept(s, log):
    sync.run(s, log, [req("Users log in with a password")], ORIGINS, now=100)
    sync.run(s, log, [req("Users log in with a password")], ORIGINS, now=200)
    sync.run(s, log, [req("Users log in with a passkey")], ORIGINS, now=300)

    assert changes(log) == [(1, "added"), (2, "modified")]
    assert store.get_version(s, "confluence:1", 1)["content"] == "Users log in with a password"
    assert store.get_version(s, "confluence:1", 2)["content"] == "Users log in with a passkey"
    assert "+Users log in with a passkey" in lookup.diff(s, "confluence:1", 1, 2)


@pytest.mark.store
def test_current_search_shows_latest_only(s, log):
    sync.run(s, log, [req("password login")], ORIGINS, now=100)
    sync.run(s, log, [req("passkey login")], ORIGINS, now=200)

    assert [h["version"] for h in store.search(s, "login")] == [2]
    assert sorted(h["version"] for h in store.search(s, "login", history=True)) == [1, 2]


@pytest.mark.store
@pytest.mark.parametrize("at, versions", [(50, []), (100, [1]), (150, [1]), (200, [2]), (250, [2])])
def test_search_as_of(s, log, at, versions):
    sync.run(s, log, [req("password login")], ORIGINS, now=100)
    sync.run(s, log, [req("passkey login")], ORIGINS, now=200)

    hits = lookup.search_as_of(s, changelog.read(log), "login", at)
    assert [h["version"] for h in hits] == versions


@pytest.mark.store
def test_removed_then_readded(s, log):
    sync.run(s, log, [req("password login")], ORIGINS, now=100)
    sync.run(s, log, [], ORIGINS, now=200)
    assert store.search(s, "login") == []
    assert store.get_version(s, "confluence:1", 1)["content"] == "password login"

    sync.run(s, log, [req("password login")], ORIGINS, now=300)
    assert changes(log) == [(1, "added"), (2, "removed"), (3, "readded")]


@pytest.mark.store
def test_unscanned_origin_is_not_removed(s, log):
    sync.run(s, log, [req("password login")], ORIGINS, now=100)
    sync.run(s, log, [], {"files:tests"}, now=200)
    assert changes(log) == [(1, "added")]


@pytest.mark.store
def test_trace_flags_tests_older_than_requirement(s, log):
    old_test = spec("def test_password_login(): pass")
    sync.run(s, log, [req("password login"), old_test], ORIGINS, now=100)
    sync.run(s, log, [req("passkey login"), old_test], ORIGINS, now=200)

    hits = lookup.trace(s, changelog.read(log), "confluence:1")
    assert [(h["key"], h["status"]) for h in hits] == [("file:tests/test_login.py", "review")]

    new_test = spec("def test_passkey_login(): pass")
    sync.run(s, log, [req("passkey login"), new_test], ORIGINS, now=300)
    hits = lookup.trace(s, changelog.read(log), "confluence:1")
    assert [h["status"] for h in hits] == ["ok"]


@pytest.mark.store
def test_long_content_is_chunked(s, log):
    body = "\n".join(f"Rule {i}: the system shall do thing {i}." for i in range(200))
    sync.run(s, log, [req(body)], ORIGINS, now=100)

    assert store.get_version(s, "confluence:1", 1)["content"] == body
    assert len(store.search(s, "system thing")) == 1


@pytest.mark.unit
@pytest.mark.confluence
def test_confluence_storage_to_text():
    html = (
        "<h1>Login</h1><p>Users <b>must</b> sign in.</p>"
        '<ac:structured-macro><ac:parameter ac:name="x">hidden</ac:parameter>'
        "<ac:rich-text-body><p>Shown</p></ac:rich-text-body></ac:structured-macro>"
        "<table><tr><td>a</td><td>b</td></tr></table>"
    )
    assert confluence.to_text(html) == "Login\nUsers must sign in.\nShown\n| a | b"


@pytest.mark.unit
@pytest.mark.confluence
@pytest.mark.parametrize(
    "labels, kind",
    [
        ([], "requirement"),
        (["test-plan"], "test_plan"),
        (["other"], "requirement"),
        (["other", "test-plan"], "test_plan"),
    ],
)
def test_confluence_label_sets_kind(labels, kind):
    page = {"metadata": {"labels": {"results": [{"name": n} for n in labels]}}}
    assert confluence.kind(page, Space("REQ"), {"test-plan": "test_plan"}) == kind
