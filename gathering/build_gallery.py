#!/usr/bin/env python3
"""Render all dist wall records as one static self-contained HTML page."""
from collections import defaultdict
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def render():
    groups = defaultdict(list)
    for path in sorted((ROOT / 'dist').rglob('*.json')):
        current = path
        while current != ROOT:
            if current.is_symlink():
                raise ValueError('symlink record path')
            current = current.parent
        record = json.loads(path.read_text(encoding='utf-8'))
        # Other dist JSON artifacts are not wall records.
        if not isinstance(record, dict) or not {'name', 'image', 'attributes'} <= record.keys():
            continue
        attrs = {item['trait_type']: item['value'] for item in record['attributes']}
        wall, number = attrs['Wall'], attrs['Number']
        if not re.fullmatch(r'https://api\.imd\.fun/artifacts/[0-9a-f]{64}', record['image']):
            raise ValueError('invalid wall image URL: ' + str(path))
        if type(number) is not int or number < 1:
            raise ValueError('invalid wall number')
        groups[wall].append((number, record, attrs))
    parts = ['''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pepeolithic — the gathering</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#201811;color:#f4e5cb;font:18px/1.6 Georgia,serif}
main{max-width:1120px;margin:auto;padding:32px 20px}h1{font-size:clamp(2rem,7vw,4rem);margin:0}
h2{border-bottom:1px solid #776047;padding-bottom:8px}p{max-width:760px}a{color:#efbc72}
nav{display:flex;gap:20px;flex-wrap:wrap}.walls{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:24px}
figure{margin:0;background:#30251a;padding:12px}img{display:block;width:100%;height:auto;aspect-ratio:1;object-fit:contain}
figcaption{padding:12px 0 0;overflow-wrap:anywhere}small{display:block;color:#d3bd9b}footer{margin-top:40px;color:#d3bd9b}
</style><main><header><h1>Pepeolithic</h1>
<p>Four lines of workers. One gathering. Each Pepe leaves a tool and a mark for the next.</p>
<p>Walls appear newest first within each line. Images load from their recorded content hashes.</p><nav>''']
    order = sorted(groups, key=lambda name: (name != 'Gathering', name))
    for i, name in enumerate(order):
        parts.append('<a href="#wall-{}">{}</a>'.format(i, escape(name)))
    parts.append('</nav></header>')
    for i, name in enumerate(order):
        parts.append('<section id="wall-{}"><h2>{}</h2><div class="walls">'.format(i, escape(name)))
        for number, record, attrs in sorted(groups[name], key=lambda item: item[0], reverse=True):
            title = escape(str(record['name']))
            url = escape(record['image'], quote=True)
            parts.append('<figure><a href="{}"><img src="{}" alt="{} — {} mark {}" loading="lazy" width="1024" height="1024"></a><figcaption>{:02d} · {}<small>Left behind: {}</small></figcaption></figure>'.format(
                url, url, escape(name, quote=True), escape(str(record['name']), quote=True), number,
                number, title, escape(str(attrs['Left behind']))))
        parts.append('</div></section>')
    parts.append('<footer>Tools and checks are local evidence. They do not certify authorship, truth or safety.</footer></main></html>')
    return '\n'.join(parts) + '\n'


if __name__ == '__main__':
    (ROOT / 'dist/index.html').write_text(render(), encoding='utf-8')
    print('Built dist/index.html')
