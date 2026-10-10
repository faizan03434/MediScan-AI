"""Aggregate CO2Wounds mask and provider-split checks; never infer patient identity."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def photos(directory):
    return {p.stem: p for p in directory.iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}}


def pixels(path):
    with Image.open(path) as image:
        rgb = image.convert('RGB')
        return hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()


def check(root):
    canonical, masks = photos(root / 'imgs'), photos(root / 'masks')
    mismatch, unexpected_values, empty = 0, 0, 0
    for key, path in masks.items():
        if key not in canonical:
            continue
        with Image.open(path) as mask, Image.open(canonical[key]) as image:
            mismatch += mask.size != image.size
            values = np.asarray(mask.convert('L'))
            observed = set(np.unique(values))
            unexpected_values += not (observed.issubset({0, 1}) or observed.issubset({0, 255}))
            empty += not bool(np.any(values))
    assignments = defaultdict(set)
    split_counts, unmatched, differing_copies = {}, 0, 0
    canonical_hashes = {key: pixels(path) for key, path in canonical.items()}
    for split in ('train', 'val', 'test'):
        entries = photos(root / 'split' / split)
        split_counts[split] = len(entries)
        for key, path in entries.items():
            digest = pixels(path)
            assignments[digest].add(split)
            unmatched += key not in canonical
            differing_copies += key in canonical and digest != canonical_hashes[key]
    annotation = json.loads((root / 'annotations/annotations.json').read_text())
    image_ids = {row['id'] for row in annotation['images']}
    annotation_stems = {Path(row['file_name']).stem for row in annotation['images']}
    return {
        'canonical_photo_count': len(canonical),
        'unique_canonical_pixels': len(set(canonical_hashes.values())),
        'mask_count': len(masks), 'mask_without_photo': len(set(masks) - set(canonical)),
        'mask_dimension_mismatches': mismatch, 'non_binary_masks': unexpected_values,
        'empty_masks': empty, 'provider_split_counts': split_counts,
        'provider_split_missing_canonical': unmatched, 'provider_copy_pixel_mismatches': differing_copies,
        'pixel_groups_crossing_provider_splits': sum(len(splits) > 1 for splits in assignments.values()),
        'annotation_image_count': len(image_ids), 'annotation_region_count': len(annotation['annotations']),
        'annotation_image_without_mask': len(annotation_stems - set(masks)),
        'annotation_orphan_regions': sum(row['image_id'] not in image_ids for row in annotation['annotations']),
        'patient_identity_verified': False, 'calibrated_measurement_labels': False,
        'training_ready': False, 'clinical_ready': False, 'commercial_ready': False,
        'limitations': ['Provider split is not verified patient-disjoint.',
                        'Source license disagreement requires review.',
                        'Masks do not provide centimeter scale or longitudinal healing labels.'],
    }


if __name__ == '__main__':
    intake = Path(__file__).resolve().parents[1] / 'datasets/kaggle/co2wounds_v1'
    result = check(next(p for p in (intake / 'raw').iterdir() if p.is_dir()))
    (intake / 'audit/annotation_qc.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
