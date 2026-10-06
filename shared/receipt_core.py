#!/usr/bin/env python3
# Adapted from line 3 handoff-check by gathering 01; workspace root adjusted.
"""Offline, workspace-confined file receipts; Python standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 64 * 1024 * 1024
SIGNATURE = b'\x89PNG\r\n\x1a\n'


def local(name):
    if not isinstance(name, str) or not name:
        raise ValueError('expected a nonempty workspace-relative path')
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('path must be relative and contain no parent traversal')
    path = ROOT / relative
    # Reject symlinks, including ones pointing back inside the workspace.
    current = ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink paths are not supported')
    if not path.is_file():
        raise ValueError('not a regular file: ' + name)
    return path


def read_local(name):
    with local(name).open('rb') as source:
        data = source.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('file exceeds 64 MiB limit')
    return data


def png_info(data):
    """Check chunk envelope/CRCs and basic order, not pixel decoding."""
    if not data.startswith(SIGNATURE):
        raise ValueError('invalid PNG signature')
    offset = 8
    kinds = []
    width = height = None
    idat_closed = False
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError('truncated PNG chunk')
        length = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError('truncated PNG payload')
        payload = data[offset + 8:end - 4]
        crc = struct.unpack_from('>I', data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            raise ValueError('PNG CRC mismatch')
        if not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind):
            raise ValueError('invalid PNG chunk type')
        if not kinds and kind != b'IHDR':
            raise ValueError('IHDR must be first')
        if kind == b'IHDR':
            if kinds or length != 13:
                raise ValueError('invalid or duplicate IHDR')
            width, height, depth, color, comp, filt, interlace = struct.unpack('>IIBBBBB', payload)
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if not (0 < width < 2**31 and 0 < height < 2**31):
                raise ValueError('invalid PNG dimensions')
            if depth not in depths.get(color, ()) or comp or filt or interlace not in (0, 1):
                raise ValueError('invalid PNG header fields')
        if kind == b'IDAT' and idat_closed:
            raise ValueError('nonconsecutive IDAT chunks')
        if b'IDAT' in kinds and kind != b'IDAT':
            idat_closed = True
        kinds.append(kind)
        offset = end
        if kind == b'IEND':
            if length or b'IDAT' not in kinds or end != len(data):
                raise ValueError('invalid PNG end or missing image data')
            return {'format': 'PNG', 'width': width, 'height': height,
                    'check': 'chunk-envelope-crc-header', 'pixels_decoded': False}
    raise ValueError('missing PNG IEND')


def describe(name):
    data = read_local(name)
    item = {'path': Path(name).as_posix(), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}
    if data.startswith(SIGNATURE) or Path(name).suffix.lower() == '.png':
        item['image'] = png_info(data)
    return item


def receipt(names):
    items = [describe(name) for name in names]
    if len({item['path'] for item in items}) != len(items):
        raise ValueError('duplicate paths')
    return {'schema': 'handoff-check/v1', 'files': items}


def verify(document):
    if not isinstance(document, dict) or set(document) != {'schema', 'files'}:
        raise ValueError('invalid receipt keys')
    if document['schema'] != 'handoff-check/v1' or not isinstance(document['files'], list) or not document['files']:
        raise ValueError('unsupported or empty receipt')
    names = []
    for item in document['files']:
        if not isinstance(item, dict) or 'path' not in item:
            raise ValueError('invalid file entry')
        names.append(item['path'])
    actual = receipt(names)
    if actual != document:
        raise ValueError('receipt differs from current bytes or metadata')
    return {'ok': True, 'verified_files': len(names)}


def demo():
    # One RGB pixel, created only in memory. No image fixture is saved.
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    tiny = SIGNATURE + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    tiny += chunk(b'IDAT', zlib.compress(b'\x00\x80\x60\x40')) + chunk(b'IEND', b'')
    assert png_info(tiny)['width'] == 1
    rejected = 0
    for bad in (tiny[:-1], tiny + b'x', tiny[:29] + bytes([tiny[29] ^ 1]) + tiny[30:]):
        try:
            png_info(bad)
        except ValueError:
            rejected += 1
    assert rejected == 3
    name = Path(__file__).relative_to(ROOT).as_posix()
    result = verify(receipt([name]))
    altered = receipt([name])
    altered['files'][0]['sha256'] = '0' * 64
    try:
        verify(altered)
    except ValueError:
        pass
    else:
        raise AssertionError('tampered receipt accepted')
    for unsafe in ('../escape', '/etc/passwd'):
        try:
            local(unsafe)
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe path accepted')
    return {'ok': True, 'in_memory_png': '1x1 RGB', 'bad_pngs_rejected': rejected,
            'self_receipt': result, 'tamper_rejected': True, 'unsafe_paths_rejected': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    create = commands.add_parser('create')
    create.add_argument('paths', nargs='+', help='paths relative to workspace root')
    check = commands.add_parser('verify')
    check.add_argument('receipt', help='workspace-relative JSON receipt path')
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'create':
            result = receipt(args.paths)
        else:
            result = verify(json.loads(read_local(args.receipt)))
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
