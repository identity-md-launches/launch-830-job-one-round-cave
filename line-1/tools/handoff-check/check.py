#!/usr/bin/env python3
"""Workspace-confined, offline SHA-256 handoff manifests. Standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile


def confined(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('file names must be nonempty relative paths')
    path = root / name
    if '..' in Path(name).parts:
        raise ValueError('parent traversal is forbidden')
    current = root
    for part in Path(name).parts:
        current /= part
        if current.is_symlink():
            raise ValueError('symlinks are forbidden')
    if not path.is_file():
        raise ValueError('missing regular file: ' + name)
    return path


def entry(root, name):
    path = confined(root, name)
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block)
            size += len(block)
    return {'path': name, 'bytes': size, 'sha256': digest.hexdigest()}


def verify(root, manifest):
    if not isinstance(manifest, dict) or set(manifest) != {'version', 'files'}:
        raise ValueError('invalid manifest fields')
    if manifest['version'] != 1 or not isinstance(manifest['files'], list):
        raise ValueError('unsupported manifest')
    seen = set()
    for item in manifest['files']:
        if not isinstance(item, dict) or set(item) != {'path', 'bytes', 'sha256'}:
            raise ValueError('invalid file entry')
        name = item['path']
        if not isinstance(name, str) or name in seen:
            raise ValueError('invalid or duplicate path')
        seen.add(name)
        if type(item['bytes']) is not int or item['bytes'] < 0:
            raise ValueError('invalid byte count')
        if entry(root, name) != item:
            raise ValueError('changed file: ' + name)
    return len(seen)


def demo(root):
    # All temporary files are created inside the current workspace and removed.
    with tempfile.TemporaryDirectory(prefix='handoff-demo-', dir=root) as directory:
        base = Path(directory)
        (base / 'evidence.txt').write_text('Measured result: 42\n', encoding='utf-8')
        manifest = {'version': 1, 'files': [entry(base, 'evidence.txt')]}
        assert verify(base, manifest) == 1
        print('PASS: intact evidence verified')
        (base / 'evidence.txt').write_text('altered', encoding='utf-8')
        try:
            verify(base, manifest)
        except ValueError:
            print('PASS: changed evidence rejected')
        else:
            raise AssertionError('tampering accepted')
        for name in ('../outside', '/outside'):
            try:
                confined(base, name)
            except ValueError:
                pass
            else:
                raise AssertionError('unsafe path accepted')
        print('PASS: absolute paths and traversal rejected')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    make = sub.add_parser('create')
    make.add_argument('files', nargs='+')
    check = sub.add_parser('verify')
    check.add_argument('manifest')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    try:
        if args.command == 'demo':
            demo(Path(__file__).resolve().parent)
        elif args.command == 'create':
            names = sorted(set(args.files))
            print(json.dumps({'version': 1, 'files': [entry(root, n) for n in names]}, indent=2))
        else:
            path = confined(root, args.manifest)
            if path.stat().st_size > 100000:
                raise ValueError('manifest exceeds 100 KB')
            count = verify(root, json.loads(path.read_text(encoding='utf-8')))
            print('PASS: verified {} files'.format(count))
    except (ValueError, OSError) as error:
        parser.exit(1, 'FAIL: {}\n'.format(error))


if __name__ == '__main__':
    main()
