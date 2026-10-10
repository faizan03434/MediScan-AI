"""Image inventory and duplicate audit. Image count is not patient count or clinical validity."""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

def image_fingerprints(path):
    raw = path.read_bytes()
    with Image.open(path) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError('resolution_limit')
        image = ImageOps.exif_transpose(source).convert('RGB')
        width, height = image.size
        pixel_hash = hashlib.sha256(f'{width}x{height}:'.encode() + image.tobytes()).hexdigest()
        gray = np.asarray(image.convert('L').resize((32, 32)), dtype=np.float32)
        dct = cv2.dct(gray)[:8, :8].flatten()
        threshold = np.median(dct[1:])
        bits = 0
        for value in dct:
            bits = (bits << 1) | int(value > threshold)
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'pixel_sha256': pixel_hash,
            'phash': f'{bits:016x}', 'width': width, 'height': height, 'bytes': len(raw)}

def find_near_duplicates(rows, radius=4):
    """BK-tree search; candidates are review flags, not automatically deleted images."""
    tree = None
    candidates = []
    for index, row in enumerate(rows):
        value = int(row['phash'], 16)
        if tree is None:
            tree = [value, [index], {}]
            continue
        stack = [tree]
        while stack:
            node = stack.pop()
            distance = (value ^ node[0]).bit_count()
            if distance <= radius:
                for other in node[1]:
                    if rows[other]['pixel_sha256'] != row['pixel_sha256']:
                        candidates.append({'left': rows[other]['path'], 'right': row['path'],
                            'hamming_distance': distance, 'label_conflict': rows[other]['label'] != row['label']})
            stack.extend(child for edge, child in node[2].items() if distance - radius <= edge <= distance + radius)
        node = tree
        while True:
            distance = (value ^ node[0]).bit_count()
            if distance == 0:
                node[1].append(index)
                break
            if distance not in node[2]:
                node[2][distance] = [value, [index], {}]
                break
            node = node[2][distance]
    return candidates

def audit(directory, output, manifest_path=None):
    directory = directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows, rejected, augmented = [], [], []
    labels = {}
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for record in manifest['records']:
            target = (manifest_path.parent / record['path']).resolve()
            if not target.is_relative_to(directory):
                raise ValueError('Manifest image is outside the audited directory')
            if target in labels and labels[target]['label'] != record['label']:
                raise ValueError('Manifest contains conflicting labels for one image')
            labels[target] = record
    csv_files = []
    for path in sorted(directory.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        if path.suffix.lower() == '.csv':
            with path.open(encoding='utf-8-sig', newline='') as handle:
                reader = csv.DictReader(handle)
                fields = reader.fieldnames or []
                count = sum(1 for _ in reader)
            csv_files.append({'path': relative, 'headers': fields, 'rows': count})
        if path.suffix.lower() not in EXTENSIONS:
            continue
        if any('augment' in part.lower() for part in path.relative_to(directory).parts):
            augmented.append(relative)
            continue
        try:
            label = labels.get(path.resolve())
            if manifest_path is not None and label is None:
                rejected.append({'path': relative, 'reason': 'missing_manifest_label'})
                continue
            rows.append({'path': relative, 'label': label['label'] if label else path.parent.name,
                         'case_group': label.get('case_id') if label else None, **image_fingerprints(path),
                         'patient_group': None, 'clinical_ready': False})
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            rejected.append({'path': relative, 'reason': type(error).__name__})
    groups = defaultdict(list)
    for row in rows:
        groups[row['pixel_sha256']].append(row)
    duplicates = [{'paths': [r['path'] for r in group], 'label_conflict': len({r['label'] for r in group}) > 1}
                  for group in groups.values() if len(group) > 1]
    unique = [group[0] for group in groups.values()]
    near = find_near_duplicates(unique)
    summary = {'images_decoded': len(rows), 'exact_unique_files': len({r['sha256'] for r in rows}),
        'unique_decoded_images': len(unique), 'class_counts': dict(Counter(r['label'] for r in rows)),
        'unique_class_counts': dict(Counter(r['label'] for r in unique)),
        'excluded_augmented_images': len(augmented), 'rejected_images': len(rejected),
        'exact_duplicate_groups': len(duplicates), 'near_duplicate_candidates': len(near),
        'near_duplicate_label_conflicts': sum(r['label_conflict'] for r in near),
        'metadata_csvs': csv_files, 'patient_mapping_verified': False,
        'split_created': False, 'training_ready': False, 'clinical_ready': False,
        'next_gate': 'Verify original source, original license, patient mapping and review duplicate candidates before splitting.'}
    (output / 'image_index.jsonl').write_text('\n'.join(json.dumps(row) for row in rows) + '\n', encoding='utf-8')
    for filename, data in [('audit.json', summary), ('exact_duplicates.json', duplicates),
                           ('near_duplicates.json', near), ('rejected.json', rejected)]:
        (output / filename).write_text(json.dumps(data, indent=2), encoding='utf-8')
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    if not args.directory.is_dir():
        parser.error('Acquired image directory does not exist')
    print(json.dumps(audit(args.directory, args.output, args.manifest), indent=2))

if __name__ == '__main__':
    main()
