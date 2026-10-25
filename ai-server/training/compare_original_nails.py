"""Verify pinned original RAR against the mirror; never import Hb from another dataset."""
import hashlib
import json
import shutil
import subprocess
import uuid
from pathlib import PurePosixPath

from acquire_original_nails import DIGEST
from audit_missing_labels import ROOT


def validate_members(names):
    if len(names) > 10000:
        raise ValueError('Archive member budget exceeded')
    for name in names:
        path = PurePosixPath(name.replace('\\', '/'))
        if path.is_absolute() or ':' in name or any(ord(c) < 32 for c in name) or '..' in path.parts:
            raise ValueError('Unsafe original archive path')
        if not path.parts or path.parts[0] != 'Fingernails' or len(path.parts) > 2:
            raise ValueError('Unexpected original source layout')
        if len(path.parts) == 2 and path.suffix.lower() != '.png':
            raise ValueError('Unexpected non-image original member')


def main():
    directory = ROOT / 'datasets/original/ghana_fingernails_mendeley_2xx4j3kjg2_v1'
    archive = directory / 'Fingernails.rar'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != DIGEST:
        raise ValueError('Original archive checksum mismatch')
    tar = shutil.which('tar')
    if not tar:
        raise ValueError('A local RAR-capable tar reader is required')
    listing = subprocess.run([tar, '-tf', str(archive)], capture_output=True, text=True, check=True, timeout=30)
    names = listing.stdout.splitlines()
    validate_members(names)
    verbose = subprocess.run([tar, '-tvf', str(archive)], capture_output=True, text=True, check=True, timeout=30)
    total = 0
    for line in verbose.stdout.splitlines():
        if not line or line[0] not in '-d':
            raise ValueError('Links and special archive members are forbidden')
        if line[0] == '-':
            # Known BSD tar layout; reject unknown formats rather than guessing sizes.
            parts = line.split(maxsplit=8)
            if len(parts) != 9 or not parts[4].isdigit():
                raise ValueError('Unsupported verbose archive listing format')
            size = int(parts[4])
            if size > 20 * 1024 * 1024:
                raise ValueError('Original image exceeds byte budget')
            total += size
    if total > 512 * 1024 * 1024:
        raise ValueError('Expanded original exceeds byte budget')
    destination = directory / ('original_audit_' + uuid.uuid4().hex)
    destination.mkdir()
    subprocess.run([tar, '-xf', str(archive), '-C', str(destination)], check=True, capture_output=True, timeout=90)
    mirror = ROOT / 'datasets/kaggle/ghana_fingernails_v1'
    rows = [json.loads(line) for line in (mirror / 'audit/image_index.jsonl').read_text().splitlines() if line]
    original = {p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in destination.rglob('*.png') if p.is_file() and not p.is_symlink()}
    matched, mismatched = 0, 0
    for row in rows:
        current = hashlib.sha256((mirror / 'raw' / row['path']).read_bytes()).hexdigest()
        if current == row['sha256'] == original.get(row['path']):
            matched += 1
        else:
            mismatched += 1
    result = {'source': 'https://data.mendeley.com/datasets/2xx4j3kjg2/1', 'original_sha256': DIGEST,
        'original_archive_verified': True, 'declared_license': 'CC BY 4.0',
        'original_png_files': len(original), 'mirror_assets_compared': len(rows),
        'byte_identical_original_mirror_assets': matched, 'mismatched_assets': mismatched,
        'original_mirror_identity_verified': matched == len(rows) == len(original) and mismatched == 0,
        'hb_metadata_files_in_original_archive': 0, 'patient_identity_verified': False,
        'clinical_ground_truth_verified': False, 'clinical_approved': False,
        'limitation': 'Original-source identity and license declaration do not verify clinical labels, patient mapping, consent or commercial product acceptance.'}
    (directory / 'original_mirror_comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
