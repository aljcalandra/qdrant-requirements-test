import argparse
import json
import sys
from datetime import datetime

from reqtrack import changelog, config, embed, lookup, sources, store, sync


def main(argv=None):
    args = parser().parse_args(argv)
    cfg = config.load(args.config)
    events = changelog.read(cfg.log)
    if args.cmd == "history":
        return output(changelog.for_key(events, args.key), args.json, line_event)
    if args.cmd == "changes":
        found = changelog.since(events, lookup.to_epoch(args.since)) if args.since else events
        found = [e for e in found if not args.kind or e["kind"] in args.kind]
        return output(found, args.json, line_event)
    s = store.connect(cfg, embed.local(cfg.model))
    if args.cmd == "sync":
        docs, origins = sources.collect(cfg)
        return output(sync.run(s, cfg.log, docs, origins), args.json, line_event)
    if args.cmd == "search":
        return output(search(s, events, args), args.json, line_hit)
    if args.cmd == "show":
        doc = lookup.show(s, events, args.key, args.version)
        print(json.dumps(doc, indent=2) if args.json else doc["content"])
    if args.cmd == "diff":
        print(lookup.diff(s, args.key, args.a, args.b))
    if args.cmd == "trace":
        return output(lookup.trace(s, events, args.key, args.limit), args.json, line_trace)


def search(s, events, args):
    if args.as_of:
        return lookup.search_as_of(s, events, args.query, lookup.to_epoch(args.as_of), args.kind, args.limit)
    return store.search(s, args.query, args.kind, history=args.all_versions, limit=args.limit)


def parser():
    p = argparse.ArgumentParser(prog="reqtrack")
    p.add_argument("--config", default="reqtrack.yaml")
    p.add_argument("--json", action="store_true", help="print JSON for other tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("sync", help="read sources and store new versions")

    sp = sub.add_parser("search", help="semantic search")
    sp.add_argument("query")
    sp.add_argument("--kind", action="append", help="requirement, test_plan or test")
    sp.add_argument("--all-versions", action="store_true")
    sp.add_argument("--as-of", help="date or datetime, e.g. 2026-10-01")
    sp.add_argument("--limit", type=int, default=10)

    sp = sub.add_parser("history", help="every version of a document")
    sp.add_argument("key")

    sp = sub.add_parser("show", help="content of a version")
    sp.add_argument("key")
    sp.add_argument("--version", type=int)

    sp = sub.add_parser("diff", help="diff two versions")
    sp.add_argument("key")
    sp.add_argument("a", type=int)
    sp.add_argument("b", type=int)

    sp = sub.add_parser("trace", help="tests and test plans for a requirement")
    sp.add_argument("key")
    sp.add_argument("--limit", type=int, default=10)

    sp = sub.add_parser("changes", help="change log")
    sp.add_argument("--since", help="date or datetime")
    sp.add_argument("--kind", action="append")
    return p


def output(rows, as_json, line):
    if as_json:
        json.dump(rows, sys.stdout, indent=2)
        print()
    else:
        for r in rows:
            print(line(r))


def when(at):
    return datetime.fromtimestamp(at).strftime("%Y-%m-%d %H:%M")


def line_event(e):
    return f"{when(e['at'])}  {e['change']:<8} v{e['version']:<3} {e['kind']:<11} {e['key']}  {e['title']}"


def line_hit(h):
    return f"{h['score']:.3f}  v{h['version']:<3} {h['kind']:<11} {h['key']}  {h['title']}"


def line_trace(h):
    return f"{h['status']:<6} " + line_hit(h)


if __name__ == "__main__":
    main()
