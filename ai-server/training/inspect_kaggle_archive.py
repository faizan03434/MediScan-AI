"""Bounded remote ZIP inventory: read central directory without downloading image payloads."""
import argparse
import io
import json
import time
import zipfile
from collections import Counter
from pathlib import Path

import requests


class RangeZip(io.RawIOBase):
    def __init__(self, url):
        self.session = requests.Session()
        with self.session.get(url, headers={'Range': 'bytes=0-0'}, timeout=40, stream=True) as probe:
            probe.raise_for_status()
            if probe.status_code != 206 or not probe.headers.get('Content-Range', '').startswith('bytes 0-0/'):
                raise ValueError('Server did not honor range probe')
            self.url, self.size = probe.url, int(probe.headers['Content-Range'].split('/')[-1])
        self.position, self.received = 0, 1

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if not 0 <= target <= self.size:
            raise ValueError('Invalid ZIP seek')
        self.position = target
        return target

    def read(self, size=-1):
        size = min(self.size - self.position, size if size >= 0 else self.size - self.position)
        if size == 0:
            return b''
        if size > 12 * 1024 * 1024 or self.received + size > 24 * 1024 * 1024:
            raise ValueError('Remote inventory byte budget exceeded')
        end = self.position + size - 1
        with self.session.get(self.url, headers={'Range': f'bytes={self.position}-{end}'}, timeout=60, stream=True) as response:
            response.raise_for_status()
            expected = f'bytes {self.position}-{end}/{self.size}'
            if response.status_code != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError('Server range identity mismatch')
            content = bytearray()
            started = time.monotonic()
            for block in response.iter_content(64 * 1024):
                if time.monotonic() - started > 90:
                    raise TimeoutError('Remote inventory range exceeded its wall-time budget')
                if len(content) + len(block) > size:
                    raise ValueError('Server sent more than the requested range')
                content.extend(block)
            if len(content) != size:
                raise ValueError('Truncated ZIP range')
        self.position += size
        self.received += size
        return bytes(content)

    def close(self):
        self.session.close()
        super().close()


def inspect(ref, version, output):
    with RangeZip(f'https://www.kaggle.com/api/v1/datasets/download/{ref}?datasetVersionNumber={version}') as remote:
        with zipfile.ZipFile(remote) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            inventory = [{'path': e.filename, 'bytes': e.file_size, 'crc32': e.CRC} for e in entries]
            report = {'ref': ref, 'version': version, 'archive_bytes': remote.size,
                      'expanded_bytes': sum(e.file_size for e in entries), 'file_count': len(entries),
                      'extensions': dict(Counter(Path(e.filename).suffix.lower() for e in entries)),
                      'folders': dict(Counter(str(Path(e.filename).parent) for e in entries)),
                      'metadata_files': [e.filename for e in entries if Path(e.filename).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}],
                      'inventory_bytes_fetched': remote.received,
                      'image_payloads_downloaded': False, 'clinical_ready': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({**report, 'entries': inventory}, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ref', required=True)
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inspect(args.ref, args.version, args.output)
