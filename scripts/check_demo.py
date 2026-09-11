"""Offline validation of the committed demo, independent of ignored local data."""
import json
import math
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate_history(history):
    stations, rows = history['stations'], history['rows']
    if not stations or not rows:
        raise ValueError('Demo requires stations and historical rows')
    seen = set()
    for row in rows:
        key = (row['station'], row['date'])
        if key in seen:
            raise ValueError(f'Duplicate historical row: {key}')
        seen.add(key)
        if row['station'] not in stations or date.fromisoformat(row['date']).year != 2025:
            raise ValueError(f'Invalid station or historical year: {key}')
        for field in ['observed', 'predicted', 'persistence']:
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'Invalid {field}: {key}')
    if {r['station'] for r in rows} != set(stations):
        raise ValueError('A listed station has no historical rows')
    return dict(Counter(r['station'] for r in rows))


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and 'src' in attrs:
            self.references.append(attrs['src'])
        elif tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.references.append(attrs['href'])


def main():
    directory = ROOT/'demo/dist'
    parser = AssetParser()
    parser.feed((directory/'index.html').read_text(encoding='utf-8'))
    for ref in parser.references:
        url = urlsplit(ref)
        if url.scheme or url.netloc:
            raise ValueError('The offline demo must use local assets')
        asset = (directory/url.path).resolve()
        if not asset.is_relative_to(directory.resolve()) or not asset.is_file():
            raise ValueError(f'Missing or out-of-directory asset: {ref}')
    source = (directory/'data.js').read_text(encoding='utf-8').strip()
    prefix = 'window.HISTORY = '
    if not source.startswith(prefix) or not source.endswith(';'):
        raise ValueError('Unexpected demo data wrapper')
    counts = validate_history(json.loads(source[len(prefix):-1]))
    print(f'Validated {sum(counts.values())} historical rows across {len(counts)} stations and {len(parser.references)} local assets')


if __name__ == '__main__':
    main()
