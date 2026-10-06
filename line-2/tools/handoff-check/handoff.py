#!/usr/bin/env python3
"""Create and verify workspace-contained SHA-256 handoff manifests."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def contained(path, root):
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError("path escapes the workspace")
    return path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def run(args):
    root = Path.cwd().resolve()
    if args.command == "demo":
        # Entirely in memory: no fixture files or network needed.
        original = b"worker handoff\n"
        changed = b"worker handoff!\n"
        expected = hashlib.sha256(original).hexdigest()
        assert hashlib.sha256(original).hexdigest() == expected
        assert hashlib.sha256(changed).hexdigest() != expected
        print("PASS: intact handoff accepted; changed bytes detected")
        return 0
    if args.command == "create":
        records = []
        for name in sorted(set(args.files)):
            path = contained(root / name, root)
            if not path.is_file():
                raise ValueError("input is not a regular file: " + name)
            records.append({"path": path.relative_to(root).as_posix(),
                            "bytes": path.stat().st_size, "sha256": digest(path)})
        print(json.dumps({"version": 1, "files": records}, indent=2))
        return 0
    manifest = contained(root / args.manifest, root)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if set(data) != {"version", "files"} or type(data["version"]) is not int or data["version"] != 1 or not isinstance(data["files"], list):
        raise ValueError("invalid manifest schema")
    failed = False
    seen = set()
    for record in data["files"]:
        if not isinstance(record, dict) or set(record) != {"path", "bytes", "sha256"}:
            raise ValueError("invalid file record")
        name = record["path"]
        if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts or name in seen:
            raise ValueError("invalid or duplicate relative path")
        seen.add(name)
        expected = record["sha256"]
        if type(record["bytes"]) is not int or record["bytes"] < 0 or not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("invalid size or digest")
        path = contained(root / name, root)
        ok = path.is_file() and path.stat().st_size == record["bytes"] and digest(path) == expected
        print(("OK " if ok else "FAIL ") + json.dumps(name))
        failed |= not ok
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo")
    create = commands.add_parser("create")
    create.add_argument("files", nargs="+")
    verify = commands.add_parser("verify")
    verify.add_argument("manifest")
    try:
        return run(parser.parse_args())
    except (OSError, ValueError, TypeError, KeyError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
