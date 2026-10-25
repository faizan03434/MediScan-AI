"""Pinned original-author nail archive, bounded range chunks, no implicit training approval."""
import hashlib
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from audit_missing_labels import ROOT

SIZE = 27451390
DIGEST = '641ef99dd2b343eb00d0fc71b5062ba0a903046228440ab6b6311f81b0dc59ed'


def main():
    directory = ROOT / 'datasets/original/ghana_fingernails_mendeley_2xx4j3kjg2_v1'
    directory.mkdir(parents=True, exist_ok=True)
    target, partial = directory / 'Fingernails.rar', directory / 'Fingernails.rar.part'
    metadata = requests.get('https://data.mendeley.com/public-api/datasets/2xx4j3kjg2/files?folder_id=root&version=1', timeout=(10, 20))
    metadata.raise_for_status()
    files = metadata.json()
    selected = [f for f in files if f.get('filename') == 'Fingernails.rar']
    if len(selected) != 1:
        raise ValueError('Original source inventory changed')
    source = selected[0]['content_details']
    if source['size'] != SIZE or source['sha256_hash'] != DIGEST:
        raise ValueError('Pinned original source identity changed')
    url = source['download_url']
    if not url.startswith('https://data.mendeley.com/public-files/datasets/2xx4j3kjg2/'):
        raise ValueError('Unexpected original file URL')
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > SIZE:
        raise ValueError('Invalid retained prefix')
    chunks = directory / 'verified_range_candidates'
    chunks.mkdir(exist_ok=True)
    started = time.monotonic()

    def acquire(bounds):
        start, end = bounds
        path = chunks / f'{start}-{end}.bin'
        if path.exists() and path.stat().st_size == end - start + 1:
            return path
        temporary = path.with_suffix('.part')
        with requests.get(url, headers={'Range': f'bytes={start}-{end}'}, stream=True, timeout=(10, 20)) as response:
            response.raise_for_status()
            if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{SIZE}':
                raise ValueError('Provider did not confirm the requested byte range')
            written = 0
            with temporary.open('wb') as handle:
                for block in response.iter_content(65536):
                    written += len(block)
                    if written > end - start + 1 or time.monotonic() - started > 180:
                        raise TimeoutError('Bounded intake incomplete; retained ranges can be resumed')
                    handle.write(block)
            if written != end - start + 1:
                raise ValueError('Truncated original range')
        temporary.replace(path)
        print(f'Original nail range acquired {start}-{end}', flush=True)
        return path

    status, error_type = 'partial', None
    try:
        if not target.exists():
            ranges = [(start, min(start + 4 * 1024 * 1024 - 1, SIZE - 1)) for start in range(offset, SIZE, 4 * 1024 * 1024)]
            with ThreadPoolExecutor(max_workers=4) as pool:
                paths = list(pool.map(acquire, ranges))
            assembled = directory / 'Fingernails.assembled.rar'
            with assembled.open('wb') as output:
                if partial.exists():
                    with partial.open('rb') as prefix:
                        shutil.copyfileobj(prefix, output)
                for path in paths:
                    with path.open('rb') as block:
                        shutil.copyfileobj(block, output)
            if assembled.stat().st_size != SIZE or hashlib.sha256(assembled.read_bytes()).hexdigest() != DIGEST:
                raise ValueError('Full original archive checksum failed')
            assembled.replace(target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != DIGEST:
            raise ValueError('Existing original archive integrity failed')
        status = 'original_checksum_verified_pending_annotation_and_mirror_audit'
    except (requests.RequestException, TimeoutError) as error:
        error_type = type(error).__name__
    receipt = {'source': 'https://data.mendeley.com/datasets/2xx4j3kjg2/1', 'status': status,
        'source_sha256': DIGEST, 'expected_bytes': SIZE, 'source_checksum_verified': status.startswith('original_checksum_verified'),
        'retained_prefix_bytes': offset, 'declared_license': 'CC BY 4.0', 'error_type': error_type,
        'clinical_approved': False, 'patient_identity_verified': False}
    (directory / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
