"""Strict patient-group splits from explicitly mapped metadata; missing IDs fail closed."""
import argparse
import csv
import hashlib
import json
import random
import os
from collections import Counter
from pathlib import Path

def build_split(index, metadata, image_column, patient_column, namespace, seed=42):
    lookup = {}
    for row in metadata:
        name, patient = row.get(image_column, '').strip(), row.get(patient_column, '').strip()
        if not name or not patient:
            raise ValueError('Every metadata row must have an image and patient identifier')
        if name in lookup and lookup[name] != patient:
            raise ValueError('Conflicting patient metadata for one image')
        lookup[name] = patient
    basenames = Counter(Path(row['path']).name for row in index)
    parent = list(range(len(index)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b):
        parent[find(a)] = find(b)
    patients, hashes, mapped = {}, {}, []
    for i, row in enumerate(index):
        name = row['path']
        if name not in lookup:
            basename = Path(name).name
            if basenames[basename] != 1 or basename not in lookup:
                raise ValueError('Missing or ambiguous patient mapping; image-level split is not allowed')
            name = basename
        patient = hashlib.sha256((namespace + ':' + lookup[name]).encode()).hexdigest()
        if patient in patients:
            union(i, patients[patient])
        patients[patient] = i
        pixel_hash = row['pixel_sha256']
        if pixel_hash in hashes:
            other = hashes[pixel_hash]
            if index[other]['label'] != row['label']:
                raise ValueError('Conflicting labels on duplicate images need review')
            union(i, other)
        hashes[pixel_hash] = i
        mapped.append({**row, 'patient_group': patient})
    groups = {}
    for i in range(len(mapped)):
        groups.setdefault(find(i), []).append(i)
    if len(groups) < 10:
        raise ValueError('Too few independent patient/duplicate groups for this split')
    strata = {}
    for group, members in groups.items():
        signature = tuple(sorted({mapped[i]['label'] for i in members}))
        strata.setdefault(signature, []).append(group)
    rng = random.Random(seed)
    for signature in sorted(strata):
        group_ids = sorted(strata[signature])
        if len(group_ids) < 3:
            raise ValueError('Too few independent groups in a label stratum for train/val/test coverage')
        rng.shuffle(group_ids)
        holdout = max(1, round(len(group_ids) * .15))
        train_end = len(group_ids) - 2 * holdout
        val_end = len(group_ids) - holdout
        for position, group in enumerate(group_ids):
            split = 'train' if position < train_end else 'val' if position < val_end else 'test'
            for i in groups[group]:
                mapped[i]['split'] = split
    classes = {r['label'] for r in mapped}
    counts = {s: dict(Counter(r['label'] for r in mapped if r['split'] == s)) for s in ['train', 'val', 'test']}
    if any(set(v) != classes for v in counts.values()):
        raise ValueError('A split is missing a class; improve cohort coverage before training')
    return {'seed': seed, 'split_unit': 'patient_and_exact_duplicate_connected_group',
        'stratification': 'group_label_signature',
        'patient_mapping_complete': True, 'patient_identity_semantics_verified': False,
        'clinical_ready': False, 'commercial_release_allowed': False,
        'group_count': len(groups), 'class_counts': counts,
        'limitations': ['Patient ID semantics must be verified against original documentation',
            'Near-duplicate candidates require review before training',
            'No independent Pakistan clinical validation', 'Source licenses still apply'], 'records': mapped}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--image-column', required=True)
    parser.add_argument('--patient-column', required=True)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--image-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    index = [json.loads(line) for line in args.index.read_text(encoding='utf-8').splitlines() if line]
    with args.metadata.open(encoding='utf-8-sig', newline='') as handle:
        metadata = list(csv.DictReader(handle))
    result = build_split(index, metadata, args.image_column, args.patient_column, args.namespace)
    image_root = args.image_root.resolve()
    for row in result['records']:
        source = (image_root / row['path']).resolve()
        if not source.is_relative_to(image_root) or not source.is_file():
            raise ValueError('Split image path is missing or outside image root')
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Split image integrity mismatch')
        row['path'] = Path(os.path.relpath(source, args.output.parent.resolve())).as_posix()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2))

if __name__ == '__main__':
    main()
