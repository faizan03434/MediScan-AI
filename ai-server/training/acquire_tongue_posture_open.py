"""Pinned open sources; verified bytes are research candidates, not diagnoses."""
import argparse
import hashlib
import json
from pathlib import Path

import requests

from acquire_skin_kaggle import download, safe_extract

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'tongue_coating': (20970467, 'images.zip', 130365716, '6f2e6d716376e3f5f92671a66f82435b'),
    'sitting_posture': (14230872, 'data.csv', 9327935, '7efbc94d653acf32eefecec3ff26d6c6'),
}


def verify_metadata(metadata, record, filename, size, digest):
    if metadata.get('id') != record or metadata.get('metadata', {}).get('access_right') != 'open':
        raise ValueError('Source identity/access changed')
    if metadata['metadata'].get('license', {}).get('id') != 'cc-by-4.0':
        raise ValueError('Source license changed')
    files = [f for f in metadata.get('files', []) if f['key'] == filename]
    if len(files) != 1 or files[0]['size'] != size or files[0]['checksum'] != 'md5:' + digest:
        raise ValueError('Source file identity changed; review a new version')
    return files[0]


def file_digest(path, algorithm):
    result = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def download_csv(url, path, size, digest):
    partial = path.with_suffix('.part')
    for attempt in range(4):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset == size and file_digest(partial, 'md5') == digest:
            partial.replace(path)
            return
        try:
            with requests.get(url, headers={'Range': f'bytes={offset}-'} if offset else {},
                              stream=True, timeout=(15, 45)) as response:
                response.raise_for_status()
                resume = offset > 0 and response.status_code == 206
                if resume and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                    raise ValueError('Unexpected resume range')
                written = offset if resume else 0
                with partial.open('ab' if resume else 'wb') as handle:
                    for block in response.iter_content(65536):
                        written += len(block)
                        if written > size:
                            raise ValueError('Unexpected source size')
                        handle.write(block)
            if partial.stat().st_size != size or file_digest(partial, 'md5') != digest:
                raise ValueError('Source checksum failed')
            partial.replace(path)
            return
        except requests.RequestException:
            if attempt == 3:
                raise
            print('CSV connection interrupted; retrying verified source with range.', flush=True)


def main(name):
    record, filename, size, digest = SOURCES[name]
    directory = ROOT / 'datasets/original' / f'{name}_zenodo_{record}'
    directory.mkdir(parents=True, exist_ok=True)
    response = requests.get(f'https://zenodo.org/api/records/{record}', timeout=30)
    response.raise_for_status()
    metadata = response.json()
    verify_metadata(metadata, record, filename, size, digest)
    (directory / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    path = directory / filename
    url = f'https://zenodo.org/records/{record}/files/{filename}?download=1'
    if filename.endswith('.zip'):
        download(url, path, max_bytes=size)
    elif not path.exists():
        download_csv(url, path, size, digest)
    if path.stat().st_size != size or file_digest(path, 'md5') != digest:
        raise ValueError('Source checksum failed')
    receipt = {'source': f'https://zenodo.org/records/{record}', 'license': 'CC BY 4.0',
        'source_checksum_verified': True, 'sha256': file_digest(path, 'sha256'),
        'bytes': size, 'clinical_ready': False, 'clinical_ground_truth_reviewed': False,
        'patient_identity_verified': False, 'status': 'acquired_pending_annotation_audit',
        'scope': 'tongue coating appearance' if name == 'tongue_coating' else 'sitting posture; not scoliosis',
        'clinical_diagnosis_supported': False}
    if filename.endswith('.zip'):
        receipt['extracted_members'] = safe_extract(path, directory / 'raw', max_expanded=500 * 1024 * 1024)
    (directory / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, choices=SOURCES)
    main(parser.parse_args().source)
