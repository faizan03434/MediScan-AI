"""Pinned public mirror intake for provenance/annotation review; never enables training."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from acquire_skin_kaggle import download, get_with_retry, parallel_download, safe_extract, sha256
from skin_data_audit import audit

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'wound_rollas': {'ref': 'rollas/wound-segmentation-dataset', 'version': 1,
        'original': 'https://www.kaggle.com/datasets/leoscode/wound-segmentation-images',
        'license_review': 'Mirror MIT; derived images cite Medetec and other wound research. Original image permissions and attribution remain unverified.',
        'scope': 'Candidate three-class clinical wound segmentation; 2760 photo/mask pairs in inventory. Not calibrated cm measurements or longitudinal healing diagnoses'},
    'retina_eye_classification': {'ref': 'gunavenkatdoddi/eye-diseases-classification', 'version': 1,
        'original': None,
        'license_review': 'Database license with original-author contents; aggregated image permissions/patient mapping require review.',
        'scope': 'Fundus research only: normal/cataract/glaucoma/diabetic retinopathy; never external-eye phone photos'},
    'eye_conjunctivitis_alisofiya': {'ref': 'alisofiya/conjunctivitis', 'version': 1,
        'original': None, 'license_review': 'Mirror Unknown; source, patient identity and diagnostic labels unverified.',
        'scope': 'Conjunctivitis candidate images; external-eye modality and labels require review'},
    'eye_conjunctivitis_revengerdna': {'ref': 'revengerdna/conjunctivitis-dataset', 'version': 1,
        'original': None, 'license_review': 'Mirror MIT; original image rights and clinical provenance unverified.',
        'scope': 'Conjunctivitis candidate images; duplicate mirrors and class coverage require review'},
    'golla_fingernail_detection': {'ref': 'abhinavgolla/fingernail-anemia-detection', 'version': 1,
        'original': None,
        'license_review': 'Kaggle Unknown; original source, label definitions and augmentation lineage unverified. No training or product release cleared.',
        'scope': 'Mirror Anemic/NonAnemic nail folder labels only; no Hb or patient metadata in remote inventory'},
    'ghana_fingernails': {'ref': 'kritagyadev/anemia-using-fingernails-image-datasets-from-ghana', 'version': 1,
        'original': 'https://data.mendeley.com/datasets/2xx4j3kjg2/1',
        'license_review': 'Original declares CC BY 4.0; mirror license Unknown. Verify source identity/attribution before training; commercial readiness is not established.',
        'scope': 'Pediatric Ghana fingernail photos; source reports 710 originals and 4260 augmented assets, not 4260 independent patients'},
    'cp_anemic': {'ref': 'karankumar4090/cp-anemic-dataset-same', 'version': 1,
        'original': 'https://data.mendeley.com/datasets/m53vz6b7fx/1',
        'license_review': 'Original CC BY 4.0 with academic-only notice; latest original v2 explicitly excludes commercial use without authorization. Mirror Apache does not clear rights.',
        'scope': 'Pediatric Ghana conjunctival pallor research; patient/Hb mapping and duplicate review required'},
    'co2wounds': {'ref': 'orvile/leprosy-chronic-wound-images-co2wounds-v2', 'version': 1,
        'original': 'https://data.mendeley.com/datasets/s2w7rjwz49/2',
        'license_review': 'Original Mendeley CC BY-NC 3.0; original GitHub states CC BY-NC-ND. Resolve discrepancy before training/release.',
        'scope': 'Chronic leprosy wound segmentation; no calibrated cm or healing-stage labels established'},
    'eyes_defy_anemia': {'ref': 'harshwardhanfartale/eyes-defy-anemia', 'version': 1,
        'original': 'https://ieee-dataport.org/documents/eyes-defy-anemia',
        'license_review': 'Kaggle declares CC BY-SA 4.0; original license/access provenance still requires verification.',
        'scope': 'Controlled-light eye images and hemoglobin metadata; 218 originals reported, not all files independent patients'},
    'biohit_tongue': {'ref': 'thngdngvn/biohit-tongue-image-dataset', 'version': 1,
        'original': 'https://github.com/BioHit/TongeImageDataset',
        'license_review': 'Mirror Apache 2.0; original repository has no explicit dataset license. Permission not established.',
        'scope': 'Tongue region segmentation only; no deficiency/infection diagnoses'},
}


def acquire(name, serial=False):
    source = SOURCES[name]
    directory = ROOT / 'datasets/kaggle' / (name + '_v1')
    directory.mkdir(parents=True, exist_ok=True)
    response = get_with_retry('https://www.kaggle.com/api/v1/datasets/view/' + source['ref'], timeout=30)
    response.raise_for_status()
    metadata = response.json()
    if metadata.get('currentVersionNumber') != source['version']:
        raise ValueError('Source version changed; review before acquiring')
    (directory / 'kaggle_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    url = f"https://www.kaggle.com/api/v1/datasets/download/{source['ref']}?datasetVersionNumber={source['version']}"
    archive = directory / 'source.zip'
    if serial:
        chunks = directory / 'chunks'
        state_path = chunks / 'source.json'
        partial = archive.with_suffix('.zip.part')
        if not archive.exists() and state_path.exists():
            state = json.loads(state_path.read_text())
            with get_with_retry(url, headers={'Range': 'bytes=0-0'}, stream=True, timeout=(15, 30)) as probe:
                probe.raise_for_status()
                if (probe.status_code != 206 or probe.headers.get('ETag') != state['etag']
                        or probe.headers.get('Content-Range') != f"bytes 0-0/{state['bytes']}"):
                    raise ValueError('Serial resume source identity mismatch')
            if not partial.exists():
                with partial.open('wb') as handle:
                    index = 0
                    while True:
                        chunk = chunks / f'{index:04d}.bin'
                        digest = chunk.with_suffix('.sha256')
                        expected = min(state['chunk_size'], state['bytes'] - index * state['chunk_size'])
                        if (expected <= 0 or not chunk.exists() or not digest.exists()
                                or chunk.stat().st_size != expected or sha256(chunk) != digest.read_text()):
                            break
                        handle.write(chunk.read_bytes())
                        index += 1
                print(f'Serial resume seeded {partial.stat().st_size // (1024 * 1024)} MiB', flush=True)
        download(url, archive, max_bytes=1024 * 1024 * 1024)
    else:
        parallel_download(url, archive, max_bytes=1024 * 1024 * 1024)
    extracted = safe_extract(archive, directory / 'raw', max_expanded=1200 * 1024 * 1024)
    receipt = {**source, 'dataset': name, 'acquired_at': datetime.now(timezone.utc).isoformat(),
        'archive_bytes': archive.stat().st_size, 'archive_sha256': sha256(archive),
        'mirror_declared_license': metadata.get('licenseName'), 'extracted_members': extracted,
        'clinical_ready': False, 'training_ready': False, 'commercial_release_allowed': False,
        'status': 'quarantine_for_provenance_and_annotation_review'}
    (directory / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2), flush=True)
    report = audit(directory / 'raw', directory / 'audit')
    report['asset_count_is_not_clinical_image_count'] = True
    report['scope'] = source['scope']
    (directory / 'audit/audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', choices=list(SOURCES), required=True)
    acquire(parser.parse_args().dataset)
