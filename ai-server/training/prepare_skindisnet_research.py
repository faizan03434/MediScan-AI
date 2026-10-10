"""Prepare the acquired mirror without changing source labels or enabling inference."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from build_patient_skin_split import build_split


def prepare(root):
    audit = root / 'audit'
    index = [json.loads(line) for line in (audit / 'image_index.jsonl').read_text().splitlines() if line]
    near = json.loads((audit / 'near_duplicates.json').read_text())
    excluded = {pair[key] for pair in near for key in ('left', 'right')}
    with (root / 'raw/SkinDisNet_3/SkinDisNet_Metadata.csv').open(encoding='utf-8-sig', newline='') as handle:
        metadata = list(csv.DictReader(handle))
    normalized = [{'image_path': f"SkinDisNet_3/Processed/{row['Folder_name']}/{row['Image_id']}.jpg",
                   'patient_id': row['Patient_id']} for row in metadata]
    if len({row['image_path'] for row in normalized}) != len(normalized):
        raise ValueError('Repeated image metadata requires review')
    if {row['path'] for row in index} != {row['image_path'] for row in normalized}:
        raise ValueError('Original metadata does not exactly match acquired images')
    accepted = [row for row in index if row['path'] not in excluded]
    result = build_split(accepted, normalized, 'image_path', 'patient_id', 'SkinDisNet_original_v2')
    output = root / 'research_patient_manifest.json'
    image_root = (root / 'raw').resolve()
    for row in result['records']:
        source = (image_root / row['path']).resolve()
        if not source.is_relative_to(image_root) or not source.is_file():
            raise ValueError('Missing or unsafe image path')
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Image integrity mismatch')
        row['path'] = Path(os.path.relpath(source, output.parent.resolve())).as_posix()
    with (audit / 'normalized_patient_metadata.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['image_path', 'patient_id'])
        writer.writeheader()
        writer.writerows(normalized)
    (audit / 'research_index.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in accepted), encoding='utf-8')
    quarantine = {'policy': 'Exclude every near-duplicate candidate endpoint; retain raw images for expert review',
                  'excluded_images': len(excluded), 'remaining_images': len(accepted),
                  'clinical_ready': False, 'paths': sorted(excluded)}
    (audit / 'quarantine_manifest.json').write_text(json.dumps(quarantine, indent=2), encoding='utf-8')
    result['source_license'] = 'Original CC BY-NC 4.0; mirror Apache declaration does not clear commercial use'
    result['near_duplicate_policy'] = quarantine['policy']
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return {key: value for key, value in result.items() if key != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / 'datasets/kaggle/skindisnet_3_v1')
    print(json.dumps(prepare(parser.parse_args().root), indent=2))
