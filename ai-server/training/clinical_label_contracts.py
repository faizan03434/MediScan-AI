"""Validate supplied reference-data structure; never authenticate clinicians or approve a model."""
import hashlib
import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

HEX = re.compile(r'^[a-fA-F0-9]{64}$')
ATTRIBUTES = {'pale', 'tip_side_red', 'red_spots', 'ecchymosis', 'cracks', 'tooth_marks', 'thick_coating', 'yellow_coating'}
TASKS = {'tongue_appearance': 'tongue_external_photo', 'tongue_disease': 'tongue_external_photo',
    'fingernail_anemia': 'fingernail_photo', 'scoliosis_phone_screening': 'back_photo',
    'scoliosis_radiographic_reference': 'back_photo', 'conjunctival_anemia': 'conjunctiva_photo',
    'skin_disease': 'clinical_skin_photo', 'external_eye_disease': 'external_eye_photo',
    'retinal_disease': 'fundus_photo', 'wound_segmentation': 'wound_photo'}
DIAGNOSTIC_REFERENCES = {'skin_disease': 'dermatologist_diagnostic_report',
    'external_eye_disease': 'ophthalmologist_diagnostic_report',
    'retinal_disease': 'ophthalmologist_fundus_report'}


def evidence(root, value):
    if not isinstance(value, dict) or not isinstance(value.get('sha256'), str) or not HEX.fullmatch(value['sha256']):
        raise ValueError('Missing evidence digest')
    relative = value.get('path', '')
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts or ':' in relative or '\\' in relative:
        raise ValueError('Unsafe evidence path')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.is_symlink():
        raise ValueError('Missing or external evidence file')
    if hashlib.sha256(path.read_bytes()).hexdigest().lower() != value['sha256'].lower():
        raise ValueError('Evidence integrity mismatch')
    return path


def validate_reference_manifest(manifest, evidence_root):
    root = Path(evidence_root)
    task = manifest.get('task')
    if task not in TASKS:
        raise ValueError('Unsupported clinical reference task')
    rights = manifest.get('rights', {})
    if rights.get('status') not in {'declared_open_license_reviewed', 'written_permission_received'}:
        raise ValueError('Pending/requested permission is not a grant')
    uses = rights.get('permitted_uses', [])
    if not isinstance(uses, list) or manifest.get('intended_use') not in {'research', 'commercial_development'} or manifest['intended_use'] not in uses:
        raise ValueError('Intended use not covered by supplied rights evidence')
    evidence(root, rights.get('evidence'))
    evidence(root, manifest.get('annotation_protocol'))
    if manifest.get('data_use_basis') not in {'licensed_research_dataset', 'consented_collection'}:
        raise ValueError('Explicit data-use basis required')
    evidence(root, manifest.get('privacy_review'))
    records = manifest.get('records', [])
    if not isinstance(records, list) or not records:
        raise ValueError('No independently reviewed records supplied')
    subjects, images = {}, set()
    for row in records:
        subject, digest = row.get('subject_pseudonym', ''), row.get('image_sha256', '')
        if not isinstance(subject, str) or not isinstance(digest, str) or not HEX.fullmatch(subject) or not HEX.fullmatch(digest):
            raise ValueError('Hashed subject/image identities required; no direct patient identifiers')
        subject, digest = subject.lower(), digest.lower()
        split = row.get('split')
        if split not in {'train', 'validation', 'calibration', 'test', 'external_test'}:
            raise ValueError('Explicit split required')
        if subject in subjects and subjects[subject] != split:
            raise ValueError('Subject split leakage')
        if digest in images:
            raise ValueError('Repeated image identity requires deduplication/adjudication')
        subjects[subject] = split
        images.add(digest)
        if row.get('modality') != TASKS[task]:
            raise ValueError('Modality does not match the camera task; radiographs and gait data are separate')
        reviewers = [row.get('reviewer_id'), row.get('second_reviewer_id')]
        if row.get('review_status') != 'adjudicated' or any(not isinstance(v, str) or not v.strip() for v in reviewers) or reviewers[0].strip() == reviewers[1].strip():
            raise ValueError('Two distinct reviewer references and an adjudication result are required')
        evidence(root, row.get('reference_evidence'))
        if task in DIAGNOSTIC_REFERENCES or task == 'wound_segmentation':
            image_proof = row.get('image_evidence')
            evidence(root, image_proof)
            if image_proof['sha256'].lower() != digest:
                raise ValueError('Image evidence must match the reviewed image identity')
        if task == 'tongue_appearance':
            attributes = row.get('attributes', {})
            if not attributes or not set(attributes).issubset(ATTRIBUTES) or not all(type(v) is bool for v in attributes.values()):
                raise ValueError('Use documented appearance attributes, never inferred organ/disease diagnoses')
            if any(row.get(field) is not None for field in ('disease_label', 'clinical_label', 'diagnosis')):
                raise ValueError('Appearance labels cannot be presented as disease confirmation')
        elif task in {'fingernail_anemia', 'conjunctival_anemia'}:
            hb = row.get('hb_g_dl')
            if type(hb) not in (int, float) or not math.isfinite(hb) or not 0 < hb < 30 or row.get('hb_unit') != 'g/dL':
                raise ValueError('Finite, explicitly unit-labelled source Hb required')
            if row.get('reference_kind') != 'laboratory_hb_report' or row.get('clinical_label') not in {'anemic', 'non_anemic', 'indeterminate'}:
                raise ValueError('Clinician label and a laboratory reference are required')
            if type(row.get('age_months')) is not int or not 0 <= row['age_months'] <= 1500:
                raise ValueError('Age context required; label thresholds come from the reviewed protocol')
            for key in ('captured_at', 'reference_at'):
                if not row.get(key) or datetime.fromisoformat(row[key]).tzinfo is None:
                    raise ValueError('Timezone-aware capture/laboratory dates required')
            if row.get('timing_reviewed_under_protocol') is not True:
                raise ValueError('Reference timing must be reviewed under the supplied protocol')
        elif task == 'scoliosis_phone_screening':
            if row.get('reference_kind') != 'clinician_screening' or row.get('clinical_label') not in {'screen_positive', 'screen_negative', 'indeterminate'}:
                raise ValueError('Screening outcomes must not be renamed confirmed scoliosis')
        elif task == 'scoliosis_radiographic_reference':
            angle = row.get('reported_cobb_angle_degrees')
            if row.get('reference_kind') != 'radiologist_report' or type(angle) not in (float, int) or not math.isfinite(angle) or not 0 <= angle <= 180:
                raise ValueError('Radiologist reference and reported angle required; no image-derived guess')
        elif task in DIAGNOSTIC_REFERENCES:
            if row.get('reference_kind') != DIAGNOSTIC_REFERENCES[task] or not isinstance(row.get('clinical_label'), str) or not row['clinical_label'].strip():
                raise ValueError('Task-specific specialist reference and explicit clinical label required')
            if row.get('reference_method') not in {'clinical_examination', 'laboratory_confirmed', 'histopathology', 'fundus_examination', 'multimodal_adjudication'}:
                raise ValueError('Explicit clinical reference method required; folder names are not a reference standard')
            if row.get('reference_method') == 'fundus_examination' and task != 'retinal_disease':
                raise ValueError('Fundus reference cannot replace an external-eye or skin examination')
            if row.get('label_status') not in {'supported_condition', 'unknown_condition', 'indeterminate'}:
                raise ValueError('Explicit supported, unknown or indeterminate reference status required')
        elif task == 'wound_segmentation':
            if row.get('reference_kind') != 'clinician_wound_annotation':
                raise ValueError('Clinician wound annotation required, not a cell-culture assay')
            from PIL import Image
            image_path = evidence(root, row['image_evidence'])
            mask_path = evidence(root, row.get('mask_evidence'))
            with Image.open(image_path) as image, Image.open(mask_path) as mask:
                if image.width * image.height > 25_000_000 or image.size != mask.size or mask.mode not in {'1', 'L'}:
                    raise ValueError('Binary wound mask must match source image dimensions')
                values = {value for count, value in mask.getcolors(256)}
                if not values.issubset({0, 1, 255}):
                    raise ValueError('Mask must contain only documented binary foreground/background values')
                if row.get('wound_present') is not True and row.get('wound_present') is not False:
                    raise ValueError('Explicit wound presence reference required')
                if row['wound_present'] != bool(values - {0}):
                    raise ValueError('Mask contradicts the wound presence reference')
            if row.get('measurement_claimed') is not False:
                raise ValueError('Size/healing claims require a separate calibrated longitudinal protocol')
        elif row.get('reference_kind') != 'clinician_diagnostic_report' or not row.get('clinical_label'):
            raise ValueError('A separate clinician reference is required for tongue disease labels')
    return {'records_structurally_valid': len(records), 'distinct_supplied_subjects': len(subjects),
        'evidence_file_integrity_checked': True, 'clinical_approved': False, 'deployment_authorized': False,
        'limitation': 'This validates supplied structure/hashes, not reviewer identity, consent, authenticity, clinical truth or legal authority.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.manifest.stat().st_size > 20 * 1024 * 1024:
        parser.error('Reference manifest exceeds the local intake budget')
    if args.output and args.output.exists():
        parser.error('Do not overwrite an existing evidence report')
    result = validate_reference_manifest(json.loads(args.manifest.read_text(encoding='utf-8')), args.evidence_root)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
