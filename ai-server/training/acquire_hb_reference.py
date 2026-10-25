"""Acquire a pinned original Hb/photo dataset; never turn provider data into clinical approval."""
import hashlib
import json
import time
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

import requests

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = 'https://api.figshare.com/v2/articles/25867432'
SOURCE = 'https://figshare.com/collections/_/6760179'
SIZE = 91619743
MD5 = '7bd86daf16c69e370173d9a7a92474b0'
SHA256 = '447127bd69fba9f6ba78056732343798bfed0c4360ea538e88880f867e3897dd'
REVIEWED_METADATA_SHA256 = 'd9ab684e2c46643eaeda01fa053b76c6477f8b353b363e8316cb2eb7b8f2e7de'


def safe_members(archive):
    files, seen, expanded = [], set(), 0
    for info in archive.infolist():
        name = PurePosixPath(info.filename)
        if name.is_absolute() or '..' in name.parts or '\\' in info.orig_filename or '\x00' in info.orig_filename or ':' in info.filename:
            raise ValueError('Unsafe archive path')
        if info.filename.casefold() in seen or (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError('Duplicate archive member or symlink')
        seen.add(info.filename.casefold())
        expanded += info.file_size
        if expanded > 350 * 1024 * 1024 or len(seen) > 2000:
            raise ValueError('Reference archive exceeds intake budget')
        if not info.is_dir():
            if name.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.csv', '.txt', '.md'}:
                raise ValueError('Unexpected reference payload')
            files.append(info)
    return files


def main():
    directory = ROOT / 'datasets/original/hb_figshare_25867432'
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = directory / 'source_metadata.json'
    if snapshot.exists() and hashlib.sha256(snapshot.read_bytes()).hexdigest() == REVIEWED_METADATA_SHA256:
        metadata = json.loads(snapshot.read_text(encoding='utf-8'))
    else:
        response = requests.get(ARTICLE, timeout=(10, 30))
        response.raise_for_status()
        metadata = response.json()
    if metadata.get('license', {}).get('name') != 'CC0' or metadata.get('version') != 1:
        raise ValueError('Pinned source license/version changed; review before acquisition')
    original = next(f for f in metadata['files'] if f['id'] == 49504041)
    if original['size'] != SIZE or original['computed_md5'] != MD5:
        raise ValueError('Provider original identity changed')
    (directory / 'source_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    target = directory / 'data.zip'
    if not target.exists():
        partial = directory / 'data.zip.part'
        chunks = directory / 'ranges_1mb'
        chunks.mkdir(exist_ok=True)
        # Reuse previously completed larger ranges; the assembled archive still requires its pinned checksum.
        for previous in (directory / 'ranges').glob('*.bin'):
            start, end = [int(value) for value in previous.stem.split('-')]
            if start % (1024 * 1024) or end >= SIZE or previous.stat().st_size != end - start + 1:
                raise ValueError('Invalid retained range identity')
            data = previous.read_bytes()
            for offset in range(0, len(data), 1024 * 1024):
                piece_start = start + offset
                piece_end = min(piece_start + 1024 * 1024 - 1, end)
                piece = chunks / f'{piece_start}-{piece_end}.bin'
                if not piece.exists():
                    piece.write_bytes(data[offset:offset + 1024 * 1024])
        started = time.monotonic()
        sessions = threading.local()

        def acquire(bounds):
            start, end = bounds
            piece = chunks / f'{start}-{end}.bin'
            if piece.exists() and piece.stat().st_size == end - start + 1:
                return piece
            if not hasattr(sessions, 'http'):
                sessions.http = requests.Session()
            for attempt in range(4):
                if time.monotonic() - started > 300:
                    raise TimeoutError('Acquisition deadline reached; complete ranges retained for resume')
                try:
                    url = original['download_url'] if attempt % 2 else 'https://api.figshare.com/v2/file/download/49504041'
                    with sessions.http.get(url, params={'range_start': start, 'attempt': attempt}, stream=True,
                                      headers={'Range': f'bytes={start}-{end}'}, timeout=(8, 15)) as download:
                        download.raise_for_status()
                        if download.status_code != 206 or download.headers.get('Content-Range') != f'bytes {start}-{end}/{SIZE}':
                            raise ValueError('Provider did not confirm exact source byte range')
                        content = bytearray()
                        for block in download.iter_content(65536):
                            content.extend(block)
                            if time.monotonic() - started > 300:
                                raise TimeoutError('Acquisition deadline reached; complete ranges retained for resume')
                            if len(content) > end - start + 1:
                                raise ValueError('Bounded source range exceeded')
                        if len(content) != end - start + 1:
                            raise ValueError('Bounded source range incomplete')
                        temporary = piece.with_suffix('.part')
                        temporary.write_bytes(content)
                        temporary.replace(piece)
                        print(f'Hb reference range acquired {start}-{end}', flush=True)
                        return piece
                except requests.RequestException:
                    if attempt == 3:
                        raise
            raise RuntimeError('Source range unavailable')

        bounds = [(start, min(start + 1024 * 1024 - 1, SIZE - 1)) for start in range(0, SIZE, 1024 * 1024)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            pieces = list(pool.map(acquire, bounds))
        with partial.open('wb') as output:
            for piece in pieces:
                output.write(piece.read_bytes())
        if partial.stat().st_size != SIZE or hashlib.md5(partial.read_bytes()).hexdigest() != MD5 or hashlib.sha256(partial.read_bytes()).hexdigest() != SHA256:
            raise ValueError('Original checksum mismatch')
        partial.replace(target)
    if target.stat().st_size != SIZE or hashlib.md5(target.read_bytes()).hexdigest() != MD5 or hashlib.sha256(target.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Existing source archive identity mismatch')
    with zipfile.ZipFile(target) as archive:
        members = safe_members(archive)
        # Every member was validated before extracting; no executable or external path is accepted.
        extracted = directory / 'raw'
        extracted.mkdir(exist_ok=True)
        for info in members:
            destination = extracted / info.filename
            if not destination.resolve().is_relative_to(extracted.resolve()):
                raise ValueError('Extraction escaped private source root')
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(info)
            if destination.exists() and destination.read_bytes() != data:
                raise ValueError('Refusing to overwrite changed original source asset')
            destination.write_bytes(data)
    receipt = {'source': SOURCE, 'article_api': ARTICLE, 'version': 1, 'declared_license': 'CC0-1.0',
        'bytes': SIZE, 'provider_md5_verified': True, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'extracted_files': len(members), 'clinical_approved': False, 'deployment_authorized': False,
        'note': 'Provider references require mapping/duplicate/unit/cohort audit; CC0 is not clinical acceptance.'}
    (directory / 'acquisition_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (requests.RequestException, TimeoutError) as error:
        directory = ROOT / 'datasets/original/hb_figshare_25867432'
        pieces = list((directory / 'ranges_1mb').glob('*.bin'))
        pending = {'source': SOURCE, 'status': 'network_incomplete_resume_required',
            'error_type': type(error).__name__, 'retained_ranges': len(pieces),
            'retained_range_bytes': sum(p.stat().st_size for p in pieces), 'expected_bytes': SIZE,
            'source_checksum_verified': False, 'clinical_approved': False, 'deployment_authorized': False}
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'pending_acquisition.json').write_text(json.dumps(pending, indent=2), encoding='utf-8')
        print(json.dumps(pending), flush=True)
        raise SystemExit(1)
