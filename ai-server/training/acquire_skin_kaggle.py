"""Version-pinned Kaggle intake; mirrors remain quarantined until provenance is checked."""
import argparse
import hashlib
import json
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import requests
from skin_data_audit import audit

ROOT = Path(__file__).resolve().parents[1]
REF = 'samurarahman14/skindisnet-3'
VERSION = 1
DIRECTORY = ROOT / 'datasets/kaggle/skindisnet_3_v1'
ORIGINAL = 'https://data.mendeley.com/datasets/yj3md44hxg/2'

def get_with_retry(url, **kwargs):
    """Retry connection/header failures only; validation and body failures stay explicit."""
    for attempt in range(3):
        try:
            return requests.get(url, **kwargs)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def download(url, path, max_bytes=350 * 1024 * 1024):
    """Resume partial files only when the remote server confirms the byte range."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix('.zip.part')
    for attempt in range(4):
        offset = partial.stat().st_size if partial.exists() else 0
        try:
            headers = {'Range': f'bytes={offset}-'} if offset else {}
            with requests.get(url, headers=headers, stream=True, timeout=(15, 30)) as response:
                response.raise_for_status()
                resumed = offset > 0 and response.status_code == 206
                if resumed and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                    raise ValueError('Remote range does not match partial file')
                if not resumed:
                    offset = 0
                advertised = int(response.headers.get('Content-Length', 0))
                if advertised + offset > max_bytes:
                    raise ValueError('Archive exceeds the acquisition size budget')
                written = offset
                progress = path.with_name('download_progress.json')
                total_bytes = advertised + offset if advertised else None
                last_report = time.monotonic()
                with partial.open('ab' if resumed else 'wb') as handle:
                    for block in response.iter_content(64 * 1024):
                        if block:
                            written += len(block)
                            if written > max_bytes:
                                raise ValueError('Archive exceeds the acquisition size budget')
                            handle.write(block)
                            if time.monotonic() - last_report >= 20:
                                handle.flush()
                                progress.write_text(json.dumps({'status': 'downloading', 'downloaded_bytes': written,
                                    'total_bytes': total_bytes, 'updated_at': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
                                print(f'Downloaded {written // (1024 * 1024)} MiB', flush=True)
                                last_report = time.monotonic()
                if advertised and written - offset != advertised:
                    raise ValueError('Incomplete response')
            with zipfile.ZipFile(partial) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Archive integrity failed')
            partial.replace(path)
            progress.write_text(json.dumps({'status': 'download_complete', 'downloaded_bytes': written,
                'total_bytes': written}), encoding='utf-8')
            return
        except requests.RequestException as error:
            if attempt == 3:
                raise RuntimeError(f'Download incomplete ({type(error).__name__}); rerun to resume') from None
            print(f'Retrying download ({type(error).__name__})', flush=True)
            time.sleep(2)

def parallel_download(url, path, max_bytes=350 * 1024 * 1024):
    """Bounded range chunks; each completed chunk can be reused after interruption."""
    if path.exists():
        return
    with get_with_retry(url, headers={'Range': 'bytes=0-0'}, stream=True, timeout=(15, 30)) as probe:
        probe.raise_for_status()
        if probe.status_code != 206 or not probe.headers.get('Content-Range', '').startswith('bytes 0-0/'):
            raise ValueError('Server does not support bounded range acquisition; use serial mode')
        total = int(probe.headers['Content-Range'].split('/')[-1])
        if not 0 < total <= max_bytes:
            raise ValueError('Archive exceeds the acquisition size budget')
        asset_url = probe.url
        etag = probe.headers.get('ETag')
    chunks = path.parent / 'chunks'
    chunks.mkdir(exist_ok=True)
    state_path = chunks / 'source.json'
    state = {'bytes': total, 'etag': etag, 'chunk_size': 1024 * 1024}
    if state_path.exists() and json.loads(state_path.read_text()) != state:
        raise ValueError('Remote archive identity changed; keep existing chunks for review')
    state_path.write_text(json.dumps(state), encoding='utf-8')
    size = state['chunk_size']
    count = (total + size - 1) // size
    progress = path.with_name('download_progress.json')
    # Completed linear bytes are retained separately until range integrity is confirmed.
    def acquire(index):
        start = index * size
        end = min(total, start + size) - 1
        target = chunks / f'{index:04d}.bin'
        digest_file = target.with_suffix('.sha256')
        if target.exists() and digest_file.exists() and target.stat().st_size == end - start + 1:
            if sha256(target) == digest_file.read_text():
                return target.stat().st_size
        for attempt in range(3):
            try:
                with requests.get(asset_url, headers={'Range': f'bytes={start}-{end}'}, stream=True, timeout=(15, 25)) as response:
                    response.raise_for_status()
                    expected = f'bytes {start}-{end}/{total}'
                    if response.status_code != 206 or response.headers.get('Content-Range') != expected:
                        raise ValueError('Remote range mismatch')
                    if response.headers.get('ETag') != etag:
                        raise ValueError('Remote archive identity changed')
                    temporary = target.with_suffix('.part')
                    written = 0
                    started = time.monotonic()
                    with temporary.open('wb') as handle:
                        for block in response.iter_content(64 * 1024):
                            if time.monotonic() - started > 90:
                                raise requests.Timeout('Chunk body exceeded its wall-time budget')
                            written += len(block)
                            if written > end - start + 1:
                                raise ValueError('Chunk exceeds requested range')
                            handle.write(block)
                    if written != end - start + 1:
                        raise ValueError('Incomplete chunk')
                    temporary.replace(target)
                    digest_file.write_text(sha256(target), encoding='ascii')
                    return written
            except requests.RequestException:
                if attempt == 2:
                    raise RuntimeError(f'Chunk {index} incomplete; rerun to resume') from None
                time.sleep(2)
    complete = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(acquire, i) for i in range(count)]
        try:
            for future in as_completed(futures):
                complete += future.result()
                progress.write_text(json.dumps({'status': 'downloading_chunks', 'downloaded_bytes': complete,
                    'total_bytes': total, 'updated_at': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
                print(f'Checked chunks: {complete // size} / {count} MiB', flush=True)
        except Exception:
            # Cancel queued requests before waiting for the bounded active workers.
            # Otherwise one failed chunk leaves hundreds of silent requests running.
            for pending in futures:
                pending.cancel()
            progress.write_text(json.dumps({'status': 'incomplete_resume_required',
                'verified_chunk_bytes_this_run': complete, 'total_bytes': total}), encoding='utf-8')
            raise
    assembled = path.with_suffix('.assembled')
    with assembled.open('wb') as output:
        for index in range(count):
            with (chunks / f'{index:04d}.bin').open('rb') as source:
                while block := source.read(64 * 1024):
                    output.write(block)
    with zipfile.ZipFile(assembled) as archive:
        if archive.testzip() is not None:
            raise ValueError('Assembled archive integrity failed')
    assembled.replace(path)
    progress.write_text(json.dumps({'status': 'download_complete', 'downloaded_bytes': total, 'total_bytes': total}), encoding='utf-8')

def safe_extract(archive_path, destination, max_expanded=700 * 1024 * 1024):
    """Extract image/CSV members only, with path, symlink and expansion limits."""
    destination = destination.resolve()
    members = []
    targets = set()
    expanded = 0
    with zipfile.ZipFile(archive_path) as archive:
        if len(archive.infolist()) > 20000:
            raise ValueError('Archive member budget exceeded')
        for member in archive.infolist():
            path = PurePosixPath(member.filename.replace('\\', '/'))
            if path.is_absolute() or '..' in path.parts or ':' in member.filename:
                raise ValueError('Unsafe archive path')
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlinks are not accepted')
            if member.is_dir() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.csv', '.txt', '.json', '.xls', '.xlsx'}:
                continue
            target = (destination / str(path)).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Archive path escaped destination')
            if target in targets:
                raise ValueError('Archive contains duplicate normalized paths')
            targets.add(target)
            expanded += member.file_size
            if expanded > max_expanded or member.file_size > 25 * 1024 * 1024:
                raise ValueError('Archive expansion budget exceeded')
            members.append((member, target))
        for member, target in members:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('wb') as output:
                while block := source.read(1024 * 1024):
                    output.write(block)
    return len(members)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=DIRECTORY)
    parser.add_argument('--parallel', action='store_true')
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    response = requests.get('https://www.kaggle.com/api/v1/datasets/view/' + REF, timeout=30)
    response.raise_for_status()
    metadata = response.json()
    if metadata.get('currentVersionNumber') != VERSION:
        raise ValueError('Mirror version changed; audit before acquisition')
    (args.directory / 'kaggle_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    archive = args.directory / 'source.zip'
    url = f'https://www.kaggle.com/api/v1/datasets/download/{REF}?datasetVersionNumber={VERSION}'
    print('Acquiring pinned Kaggle mirror:', REF, 'version', VERSION, flush=True)
    if args.parallel:
        parallel_download(url, archive)
    else:
        download(url, archive)
    members = safe_extract(archive, args.directory / 'raw')
    receipt = {'dataset': 'SkinDisNet mirror', 'kaggle_ref': REF, 'kaggle_version': VERSION,
        'original_source': ORIGINAL, 'original_license': 'CC BY-NC 4.0',
        'mirror_declared_license': metadata.get('licenseName'),
        'license_conflict': 'Mirror Apache 2.0 does not replace original CC BY-NC 4.0',
        'acquired_at': datetime.now(timezone.utc).isoformat(), 'source_url': url,
        'archive_sha256': sha256(archive), 'archive_bytes': archive.stat().st_size,
        'extracted_members': members, 'commercial_release_allowed': False,
        'status': 'quarantine_pending_original_metadata_and_image_audit', 'clinical_ready': False}
    (args.directory / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    print('Auditing acquired images and duplicate candidates...', flush=True)
    report = audit(args.directory / 'raw', args.directory / 'audit')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
