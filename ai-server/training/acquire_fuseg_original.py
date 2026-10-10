"""Pinned original FUSeg assets; audit masks/duplicates, never claim clinical approval."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import numpy as np
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.clean_medical_intake import select_clean  # noqa: E402
from training.skin_data_audit import find_near_duplicates, image_fingerprints  # noqa: E402
from acquire_skin_kaggle import download, safe_extract  # noqa: E402

COMMIT = '42a272dfe0679f20675e826385925cb7562934b6'
PREFIX = 'data/Foot Ulcer Segmentation Challenge'
DIRECTORY = ROOT / 'datasets/original/fuseg_42a272d'


def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def target_path(root, relative):
    parts = PurePosixPath(relative)
    if parts.is_absolute() or '..' in parts.parts or ':' in relative or '\\' in relative:
        raise ValueError('Unsafe repository path')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Repository path escape')
    return path


def main(snapshot_mode=False):
    source = ROOT / 'datasets/catalog/platform_expansion/fuseg_original_tree.json'
    tree = json.loads(source.read_text())
    if tree.get('sha') != COMMIT or tree.get('truncated'):
        raise ValueError('Unexpected/truncated source inventory')
    entries = [r for r in tree['tree'] if r['type'] == 'blob' and r['path'].startswith(PREFIX + '/')
               and Path(r['path']).suffix.lower() in {'.png', '.jpg', '.jpeg'}]
    raw = DIRECTORY / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    snapshot = None
    if snapshot_mode:
        archive = DIRECTORY / 'original_repository.zip'
        download('https://codeload.github.com/uwm-bigdata/wound-segmentation/zip/' + COMMIT,
                 archive, max_bytes=700 * 1024 * 1024)
        expanded = DIRECTORY / 'snapshot'
        safe_extract(archive, expanded, max_expanded=1200 * 1024 * 1024)
        snapshot = expanded / ('wound-segmentation-' + COMMIT)
        if not snapshot.exists():
            raise ValueError('Unexpected repository snapshot root')
    def acquire(entry):
        relative = str(PurePosixPath(entry['path']).relative_to(PREFIX))
        path = target_path(raw, relative)
        if path.exists():
            if git_blob_sha(path.read_bytes()) != entry['sha']:
                raise ValueError('Existing source integrity failed')
            return
        if entry['size'] > 8 * 1024 * 1024:
            raise ValueError('Asset budget exceeded')
        if snapshot is not None:
            data = target_path(snapshot, entry['path']).read_bytes()
            if len(data) != entry['size'] or git_blob_sha(data) != entry['sha']:
                raise ValueError('Snapshot source integrity failed')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return
        url = 'https://raw.githubusercontent.com/uwm-bigdata/wound-segmentation/' + COMMIT + '/' + quote(entry['path'])
        for attempt in range(3):
            try:
                with requests.get(url, timeout=(15, 30), stream=True) as response:
                    response.raise_for_status()
                    data = bytearray()
                    for block in response.iter_content(65536):
                        if len(data) + len(block) > entry['size']:
                            raise ValueError('Unexpected source asset length')
                        data.extend(block)
                if len(data) != entry['size'] or git_blob_sha(data) != entry['sha']:
                    raise ValueError('Git blob integrity failed')
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(path.suffix + '.part')
                temporary.write_bytes(data)
                temporary.replace(path)
                return
            except requests.RequestException:
                if attempt == 2:
                    raise RuntimeError('FUSeg acquisition incomplete; rerun to resume') from None
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(acquire, entry) for entry in entries]
        try:
            for i, future in enumerate(futures):
                future.result()
                if (i + 1) % 100 == 0:
                    print(f'FUSeg verified assets: {i + 1}/{len(entries)}', flush=True)
        except Exception:
            for future in futures:
                future.cancel()
            raise
    rows, issues = [], {}
    for entry in entries:
        relative = str(PurePosixPath(entry['path']).relative_to(PREFIX))
        parts = PurePosixPath(relative).parts
        if len(parts) != 3 or parts[1] != 'images':
            continue
        row = {'path': relative, 'label': 'wound_segmentation', 'provider_split': parts[0],
               **image_fingerprints(raw / relative)}
        mask = PurePosixPath(parts[0], 'labels', parts[2])
        mask_path = raw / str(mask)
        row['mask_path'] = str(mask) if mask_path.exists() else None
        if mask_path.exists():
            with Image.open(mask_path) as image:
                values = np.asarray(image)
                if image.size != (row['width'], row['height']) or values.ndim != 2 or not set(np.unique(values)).issubset({0, 1}) or not values.any():
                    issues[relative] = ['invalid_or_empty_binary_mask']
            row['mask_sha256'] = hashlib.sha256(mask_path.read_bytes()).hexdigest()
        rows.append(row)
    groups = {}
    for row in rows:
        groups.setdefault(row['pixel_sha256'], []).append(row)
    for group in groups.values():
        if len({r['provider_split'] for r in group}) > 1:
            for row in group:
                issues.setdefault(row['path'], []).append('exact_pixel_provider_split_overlap')
        hashes = {r.get('mask_sha256') for r in group if r.get('mask_path')}
        if len(hashes) > 1:
            for row in group:
                issues.setdefault(row['path'], []).append('same_photo_different_masks_requires_review')
    near = find_near_duplicates(rows)
    accepted, quarantine, redundant = select_clean(rows, issues, near)
    other = ROOT / 'datasets/kaggle/co2wounds_v1/cleaned/manifest.json'
    cross = 0
    if other.exists():
        existing = {r['pixel_sha256'] for r in json.loads(other.read_text())['records']}
        cross = sum(r['pixel_sha256'] in existing for r in rows)
    summary = {'source': 'https://github.com/uwm-bigdata/wound-segmentation', 'commit': COMMIT,
        'source_assets_verified': len(entries), 'photo_count': len(rows),
        'annotated_photo_count': sum(bool(r['mask_path']) for r in rows),
        'retained_unique_candidates': len(accepted), 'quarantined_assets': len(quarantine),
        'provider_photo_counts': dict(Counter(r['provider_split'] for r in rows)),
        'exact_overlap_with_clean_co2wounds': cross, 'patient_identity_verified': False,
        'clinical_ready': False, 'training_ready': False, 'commercial_release_allowed': False,
        'limitations': ['No source patient-ID mapping verified; provider split is not independent-patient proof.',
            'Source permission to share does not establish a full commercial ML license.',
            'Test masks are private; clinical performance is not established.',
            'Derivative Rollas data cites this source; do not treat mirrors as independent external tests.']}
    (DIRECTORY / 'research_candidate_manifest.json').write_text(json.dumps({**summary, 'records': accepted,
        'quarantine': quarantine, 'redundant': redundant}, indent=2), encoding='utf-8')
    (DIRECTORY / 'near_candidates.json').write_text(json.dumps(near, indent=2), encoding='utf-8')
    (ROOT.parent / 'docs/FUSEG_INTAKE_RESULTS.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', action='store_true', help='Acquire one pinned ZIP rather than individual image requests')
    args = parser.parse_args()
    main(args.snapshot)
