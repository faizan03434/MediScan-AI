"""Audit existing annotations without inventing disease labels or granting permission."""
import argparse
import ast
import hashlib
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
NAIL_NAME = re.compile(r'^(Anemic|Non-anemic|Non-Anrmic)-(?:FN|Fin)-(\d+)(?: \((\d+)\))?\.png$', re.I)


def source_class_map(payload):
    text = payload.decode('utf-8-sig')
    names = re.search(r'^names:\s*(\[[^\n]+\])\s*$', text, re.M)
    count = re.search(r'^nc:\s*(\d+)\s*$', text, re.M)
    if not names or not count:
        raise ValueError('Missing explicit source class map')
    labels = ast.literal_eval(names.group(1))
    if not isinstance(labels, list) or len(labels) != int(count.group(1)) or len(set(labels)) != len(labels) or not all(isinstance(v, str) and v for v in labels):
        raise ValueError('Invalid source class map')
    return labels


def nail_identity(path):
    match = NAIL_NAME.fullmatch(PurePosixPath(path.replace('\\', '/')).name)
    if not match:
        return None, None, 'unsupported_filename'
    label, number, _ = match.groups()
    if label.casefold() == 'non-anrmic':
        return None, 'unconfirmed-non-anrmic:' + str(int(number)), 'unconfirmed_provider_spelling'
    normalized = 'Anemic' if label.casefold() == 'anemic' else 'Non-anemic'
    # Conservative augmentation family; deliberately not claimed as a verified patient ID.
    return normalized, normalized.casefold() + ':' + str(int(number)), None


def annotation_geometry(line):
    fields = line.split()
    if len(fields) < 5:
        raise ValueError('too_few_fields')
    try:
        category = int(fields[0])
        values = [float(value) for value in fields[1:]]
    except ValueError:
        raise ValueError('invalid_numeric_fields') from None
    if category < 0 or not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
        raise ValueError('invalid_class_or_coordinates')
    if len(values) == 4:
        x, y, width, height = values
        if width <= 0 or height <= 0 or min(x - width / 2, y - height / 2) < -1e-6 or max(x + width / 2, y + height / 2) > 1 + 1e-6:
            raise ValueError('invalid_box_extent')
        return category, 'box'
    if len(values) < 6 or len(values) % 2:
        raise ValueError('invalid_polygon_coordinate_count')
    points = list(zip(values[::2], values[1::2]))
    area = abs(sum(x * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * y
                   for i, (x, y) in enumerate(points))) / 2
    if area <= 1e-8:
        raise ValueError('degenerate_polygon')
    return category, 'polygon'


def nails():
    directory = ROOT / 'datasets/kaggle/ghana_fingernails_v1'
    metadata = json.loads((ROOT / 'datasets/catalog/gap_review_20261025/nails_initial_state.json').read_text())['dataset']['snapshot']
    if metadata.get('id') != '2xx4j3kjg2' or metadata.get('version') != 1 or metadata.get('licence', {}).get('short_name') != 'CC BY 4.0':
        raise ValueError('Original source/license evidence changed or is unavailable')
    rows = [json.loads(line) for line in (directory / 'audit/image_index.jsonl').read_text().splitlines() if line]
    pixels, families = defaultdict(list), defaultdict(list)
    recovered, issues = [], Counter()
    for row in rows:
        source = (directory / 'raw' / row['path']).resolve()
        if not source.is_relative_to((directory / 'raw').resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Nail source integrity/path check failed')
        label, family, issue = nail_identity(row['path'])
        candidate = {**row, 'provider_filename_label': label, 'augmentation_family': family}
        if issue:
            candidate['label_issue'] = issue
            issues[issue] += 1
        recovered.append(candidate)
        pixels[row['pixel_sha256']].append(candidate)
        if family:
            families[family].append(candidate)
    conflicting = {digest for digest, group in pixels.items()
        if len({r['provider_filename_label'] for r in group if r['provider_filename_label']}) > 1}
    # Quarantine a whole augmentation family when any exact image has conflicting labels.
    blocked_families = {r['augmentation_family'] for digest in conflicting for r in pixels[digest] if r['augmentation_family']}
    for row in recovered:
        if row['pixel_sha256'] in conflicting or row['augmentation_family'] in blocked_families:
            row['label_issue'] = 'exact_pixel_label_conflict_or_related_family'
    output = directory / 'label_gap_audit'
    output.mkdir(exist_ok=True)
    (output / 'provider_label_candidates.json').write_text(json.dumps({'records': recovered,
        'training_ready': False, 'clinical_ready': False, 'patient_identity_verified': False}, indent=2), encoding='utf-8')
    comparison_path = ROOT / 'datasets/original/ghana_fingernails_mendeley_2xx4j3kjg2_v1/original_mirror_comparison.json'
    comparison = json.loads(comparison_path.read_text()) if comparison_path.exists() else {}
    return {'task': 'fingernail_anemia', 'source': 'https://data.mendeley.com/datasets/2xx4j3kjg2/1',
        'original_declared_license': 'CC BY 4.0', 'original_license_page_verified': True,
        'original_mirror_identity_verified': comparison.get('original_mirror_identity_verified', False),
        'byte_identical_original_mirror_assets': comparison.get('byte_identical_original_mirror_assets', 0),
        'hb_metadata_files_in_original_archive': comparison.get('hb_metadata_files_in_original_archive'),
        'mirror_images': len(rows), 'unique_decoded_images': len(pixels), 'augmentation_families': len(families),
        'provider_filename_label_counts': dict(Counter(r['provider_filename_label'] or 'unresolved' for r in recovered)),
        'filename_issues': dict(issues), 'conflicting_exact_pixel_groups': len(conflicting),
        'blocked_augmentation_families': len(blocked_families),
        'candidate_images_without_detected_label_issue': sum(not r.get('label_issue') for r in recovered),
        'patient_identity_verified': False, 'hb_mapping_verified': False, 'training_ready': False,
        'clinical_ready': False, 'commercial_release_allowed': False,
        'remaining': ['Confirm original naming aliases and ambiguous Non-Anrmic spelling with the provider.',
            'Obtain authoritative image-to-subject and image-to-Hb mapping; do not infer patient identity from filenames.',
            'Resolve duplicate/conflicting annotations and establish independent clinical reference labels.']}


def tongue():
    directory = ROOT / 'datasets/original/tongue_coating_zenodo_20970467'
    archive = directory / 'images.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != 'acfead7112b7cb6e506028f74dead326b1c0ce31f598c67b5675ccfb09cf56d7':
        raise ValueError('Original tongue archive checksum failed')
    geometry, categories, invalid, split_counts = Counter(), Counter(), Counter(), Counter()
    hashes = defaultdict(set)
    class_maps, missing_pairs = [], 0
    with zipfile.ZipFile(archive) as source:
        members = {entry.filename: entry for entry in source.infolist() if not entry.is_dir()}
        for name, entry in members.items():
            if entry.file_size > 20 * 1024 * 1024 or '..' in PurePosixPath(name).parts:
                raise ValueError('Unsafe or oversized source archive member')
            path = PurePosixPath(name)
            if path.name.lower() in {'data.yaml', 'data.yml', 'classes.txt'}:
                class_maps.append(name)
            parts = path.parts
            split = next((part for part in parts if part in {'train', 'valid', 'val', 'test'}), None)
            if split is None:
                continue
            if 'images' in parts[:-1] and path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
                hashes[hashlib.sha256(source.read(name)).hexdigest()].add(split)
                split_counts[split] += 1
            if path.suffix.lower() != '.txt' or 'labels' not in parts:
                continue
            if entry.file_size > 1024 * 1024:
                raise ValueError('Annotation exceeds audit budget')
            stem = name.rsplit('/labels/', 1)[0] + '/images/' + path.stem
            if not any(stem + suffix in members for suffix in ('.jpg', '.png', '.jpeg', '.JPG', '.PNG')):
                missing_pairs += 1
            for line in source.read(name).decode('utf-8-sig').splitlines():
                if not line.strip():
                    continue
                try:
                    category, kind = annotation_geometry(line)
                    categories[str(category)] += 1
                    geometry[kind] += 1
                except ValueError as error:
                    invalid[str(error)] += 1
        if len(class_maps) != 1:
            raise ValueError('Expected one explicit source class map')
        mapping_payload = source.read(class_maps[0])
        names = source_class_map(mapping_payload)
        if any(int(category) >= len(names) for category in categories):
            raise ValueError('Annotation references unknown source class')
    return {'task': 'tongue_appearance', 'source': 'https://zenodo.org/records/20970467',
        'original_checksum_verified': True, 'declared_license': 'CC BY 4.0',
        'source_image_counts': dict(split_counts), 'numeric_class_instance_counts': dict(categories),
        'annotation_geometry_counts': dict(geometry), 'invalid_annotation_counts': dict(invalid),
        'labels_without_image_pair': missing_pairs, 'class_map_files': class_maps,
        'exact_file_cross_split_groups': sum(len(splits) > 1 for splits in hashes.values()),
        'source_class_map_verified': True, 'source_class_names': names,
        'class_map_sha256': hashlib.sha256(mapping_payload).hexdigest(),
        'class_meanings': 'Provider tongue appearance/color classes, not clinician-confirmed disease labels',
        'patient_identity_verified': False,
        'clinical_disease_labels_available': False, 'training_ready': False, 'clinical_ready': False,
        'commercial_release_allowed': False,
        'remaining': ['Keep mixed box/polygon tasks separate; exclude unsupported geometry from mask training.',
            'Review split overlap and annotation errors before deriving a training manifest.',
            'Obtain independent subject mapping and clinician-confirmed disease labels for any diagnostic claim.',
            'TongueDx academic-only access/commercial exception remains pending author approval.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'docs/LABEL_GAP_AUDIT_2026_10_25.json')
    args = parser.parse_args()
    result = {'fingernail': nails(), 'tongue': tongue(), 'clinical_inference_enabled': False}
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
