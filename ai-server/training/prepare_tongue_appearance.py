"""Source-labelled tongue appearance only; no deficiency/infection labels invented."""
import hashlib
import json
import zipfile
from collections import Counter, defaultdict

from audit_missing_labels import ROOT, annotation_geometry, source_class_map
from skin_data_audit import find_near_duplicates, image_fingerprints
from train_skin_research import validate_splits


def main():
    directory = ROOT / 'datasets/original/tongue_coating_zenodo_20970467'
    output = directory / 'appearance_manifest.json'
    if output.exists():
        raise ValueError('Immutable tongue appearance manifest already exists')
    archive = directory / 'images.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != 'acfead7112b7cb6e506028f74dead326b1c0ce31f598c67b5675ccfb09cf56d7':
        raise ValueError('Original archive checksum mismatch')
    rows, quarantine = [], []
    with zipfile.ZipFile(archive) as source:
        member_names = set(source.namelist())
        mapping = source.read('images/data.yaml')
        classes = source_class_map(mapping)
        for entry in source.infolist():
            name = entry.filename
            if '/labels/' not in name or not name.endswith('.txt'):
                continue
            annotations = [annotation_geometry(line) for line in source.read(name).decode('utf-8-sig').splitlines() if line.strip()]
            ids = {category for category, _ in annotations}
            if len(ids) != 1 or any(kind != 'polygon' for _, kind in annotations):
                quarantine.append({'annotation': name, 'reason': 'ambiguous_class_or_non_polygon_geometry'})
                continue
            stem = name.rsplit('/labels/', 1)[0] + '/images/' + name.rsplit('/', 1)[-1][:-4]
            matches = [candidate for candidate in (stem + '.jpg', stem + '.png', stem + '.jpeg') if candidate in member_names]
            if len(matches) != 1:
                raise ValueError('Missing/ambiguous image pair')
            relative = matches[0]
            path = (directory / 'raw' / relative).resolve()
            if not path.is_relative_to((directory / 'raw').resolve()) or not path.is_file():
                raise ValueError('Missing or external extracted image')
            fingerprint = image_fingerprints(path)
            if fingerprint['sha256'] != hashlib.sha256(source.read(relative)).hexdigest():
                raise ValueError('Extracted image differs from verified original ZIP')
            split = next(part for part in path.relative_to(directory / 'raw').parts if part in {'train', 'valid', 'test'})
            category = ids.pop()
            if category >= len(classes):
                raise ValueError('Unknown source class')
            rows.append({'path': relative, 'label': classes[category], 'source_class_id': category,
                'split': 'val' if split == 'valid' else split,
                'augmentation_family': path.stem.split('.rf.')[0], **fingerprint})
            if len(rows) % 500 == 0:
                print(f'Tongue source image fingerprints {len(rows)}', flush=True)
    reasons = defaultdict(set)
    for field in ('sha256', 'pixel_sha256', 'augmentation_family'):
        groups = defaultdict(list)
        for row in rows:
            groups[row[field]].append(row)
        for group in groups.values():
            if len({r['split'] for r in group}) > 1 or len({r['label'] for r in group}) > 1:
                for row in group:
                    reasons[row['path']].add('cross_split_or_label_conflict_' + field)
    near = find_near_duplicates(rows)
    by_path = {row['path']: row for row in rows}
    for pair in near:
        a, b = by_path[pair['left']], by_path[pair['right']]
        if a['split'] != b['split'] or a['label'] != b['label']:
            reasons[a['path']].add('near_duplicate_requires_review')
            reasons[b['path']].add('near_duplicate_requires_review')
    retained, seen = [], set()
    for row in rows:
        if row['path'] in reasons:
            quarantine.append({**row, 'reason': sorted(reasons[row['path']])})
        elif row['pixel_sha256'] not in seen:
            seen.add(row['pixel_sha256'])
            retained.append(row)
    splits = validate_splits(retained, 'augmentation_family')
    manifest = {'task': 'tongue_appearance', 'source': 'https://zenodo.org/records/20970467',
        'declared_license': 'CC BY 4.0', 'source_class_names': classes, 'source_class_map_verified': True,
        'class_map_sha256': hashlib.sha256(mapping).hexdigest(), 'records': retained, 'quarantine': quarantine,
        'split_identity': 'provider_image_and_export_family_not_patient', 'clinical_ready': False,
        'clinical_disease_labels_available': False, 'patient_identity_verified': False,
        'commercial_release_allowed': False, 'research_only': True,
        'limitations': ['Source normal means provider appearance category, not confirmed healthy.',
            'Color/appearance classes do not establish anemia, deficiency, infection or organ disease.',
            'Export-family/duplicate separation is not verified subject separation.']}
    output.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    summary = {k: manifest[k] for k in ('task', 'source', 'declared_license', 'source_class_names',
        'source_class_map_verified', 'class_map_sha256', 'clinical_ready', 'patient_identity_verified', 'limitations')}
    summary.update({'retained_images': len(retained), 'quarantined_images': len(quarantine),
        'class_counts': dict(Counter(r['label'] for r in retained)), 'split_counts': {s: len(v) for s, v in splits.items()}})
    (directory / 'appearance_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
