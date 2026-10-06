#!/usr/bin/env python3
"""Verify and translate plain/rich handoff receipts; offline, stdlib only."""
import argparse
import copy
import json
from pathlib import Path
import runpy
import sys

CORE = runpy.run_path(str(Path(__file__).with_name('receipt_core.py')))


def plain(rich):
    return {'version': 1, 'files': [
        {key: item[key] for key in ('path', 'bytes', 'sha256')}
        for item in rich['files']]}


def validate(document):
    if not isinstance(document, dict):
        raise ValueError('receipt must be an object')
    if set(document) == {'version', 'files'}:
        if type(document['version']) is not int or document['version'] != 1:
            raise ValueError('version must be integer 1')
        rich = False
    elif set(document) == {'schema', 'files'} and document['schema'] == 'handoff-check/v1':
        rich = True
    else:
        raise ValueError('unsupported receipt schema')
    items = document['files']
    if not isinstance(items, list) or not items:
        raise ValueError('receipt must contain files')
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('file entry must be an object')
        fields = {'path', 'bytes', 'sha256'}
        if rich and 'image' in item:
            fields.add('image')
        if set(item) != fields:
            raise ValueError('invalid entry fields')
        if type(item['bytes']) is not int or item['bytes'] < 0:
            raise ValueError('byte count must be a nonnegative integer')
        digest = item['sha256']
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('invalid SHA-256')
        if 'image' in item:
            meta = item['image']
            if not isinstance(meta, dict) or any(type(meta.get(k)) is not int for k in ('width', 'height')):
                raise ValueError('image dimensions must be integers')
            if type(meta.get('pixels_decoded')) is not bool:
                raise ValueError('pixels_decoded must be boolean')
    actual = CORE['receipt']([item['path'] for item in items])
    expected = actual if rich else plain(actual)
    if expected != document:
        raise ValueError('receipt differs from current bytes or metadata')
    return actual


def convert(document, target):
    # Verify before translation: never bless changed bytes with fresh hashes.
    rich = validate(document)
    return rich if target == 'rich' else plain(rich)


def demo():
    name = Path(__file__).resolve().relative_to(CORE['ROOT']).as_posix()
    rich = CORE['receipt']([name])
    basic = convert(rich, 'plain')
    assert convert(basic, 'rich') == rich
    bad = []
    changed = copy.deepcopy(basic)
    changed['files'][0]['sha256'] = '0' * 64
    bad.append(changed)
    bad.append({'version': True, 'files': basic['files']})
    bad.append({'version': 1, 'files': []})
    changed = copy.deepcopy(basic)
    changed['files'].append(changed['files'][0])
    bad.append(changed)
    changed = copy.deepcopy(basic)
    changed['files'][0]['path'] = '../outside'
    bad.append(changed)
    for document in bad:
        try:
            convert(document, 'rich')
        except (ValueError, OSError, TypeError):
            continue
        raise AssertionError('invalid receipt accepted')
    return {'ok': True, 'roundtrip': True, 'invalid_receipts_rejected': len(bad),
            'png_checks': CORE['demo']()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    create = commands.add_parser('create')
    create.add_argument('paths', nargs='+')
    create.add_argument('--format', choices=('plain', 'rich'), default='rich')
    verify = commands.add_parser('verify')
    verify.add_argument('receipt')
    trans = commands.add_parser('convert')
    trans.add_argument('receipt')
    trans.add_argument('--format', choices=('plain', 'rich'), required=True)
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'create':
            result = CORE['receipt'](args.paths)
            if args.format == 'plain':
                result = plain(result)
        else:
            document = json.loads(CORE['read_local'](args.receipt))
            if args.command == 'convert':
                result = convert(document, args.format)
            else:
                result = {'ok': True, 'verified_files': len(validate(document)['files'])}
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
