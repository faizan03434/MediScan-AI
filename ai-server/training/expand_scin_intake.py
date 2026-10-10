"""Acquire all eligible SCIN cases without rewriting the previously evaluated pilot split."""
import argparse
import hashlib
import io
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
from fetch_scin import ROOT, fetch
from prepare_scin_research import eligible_cases

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=ROOT / 'datasets/scin')
    args = parser.parse_args()
    pilot = json.loads((args.directory / 'research_manifest.json').read_text(encoding='utf-8'))
    locked = {r['case_id']: r['split'] for r in pilot['records']}
    eligible = eligible_cases(args.directory)
    print('Eligible original cases:', dict(Counter(r['label'] for r in eligible)), flush=True)
    def acquire(row):
        name = hashlib.sha256((row['case_id'] + row['source']).encode()).hexdigest()[:24] + '.jpg'
        path = args.directory / 'images' / name
        try:
            fetch(row['source'], path)
            raw = path.read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            return {**row, 'path': 'images/' + name, 'sha256': hashlib.sha256(raw).hexdigest(),
                    'bytes': len(raw), 'pilot_split': locked.get(row['case_id']),
                    'split': 'quarantine', 'clinical_ready': False}
        except Exception as error:
            print('Acquisition skipped:', type(error).__name__, flush=True)
            return None
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = [r for r in pool.map(acquire, eligible) if r]
    output = {'dataset': 'SCIN expansion intake', 'clinical_ready': False,
        'eligible_cases': len(eligible), 'acquired_images': len(rows),
        'class_counts': dict(Counter(r['label'] for r in rows)),
        'pilot_manifest_preserved': True, 'split_created': False,
        'limitations': ['Previously examined pilot test is not a new external test',
            'Case IDs do not establish patient identity', 'Three selected labels, no healthy/OOD control',
            'New acquisition is quarantined until duplicate and split review'], 'records': rows}
    (args.directory / 'expansion_intake.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in output.items() if k != 'records'}, indent=2))

if __name__ == '__main__':
    main()
