"""Compare acquired sources without merging their different clinical label schemes."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from skin_data_audit import find_near_duplicates

ROOT = Path(__file__).resolve().parents[1]


def compare(index_paths):
    rows = []
    for source, path in index_paths.items():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line:
                row = json.loads(line)
                rows.append({**row, 'path': source + ':' + row['path'], 'source': source})
    exact = defaultdict(list)
    for row in rows:
        exact[row['pixel_sha256']].append(row)
    overlap = [group for group in exact.values() if len({row['source'] for row in group}) > 1]
    source_by_path = {row['path']: row['source'] for row in rows}
    near = [pair for pair in find_near_duplicates(rows)
            if source_by_path[pair['left']] != source_by_path[pair['right']]]
    return {'acquired_images': len(rows), 'unique_decoded_images_across_sources': len(exact),
            'cross_source_exact_groups': len(overlap), 'cross_source_near_candidates': len(near),
            'clinical_ready': False, 'labels_merged': False,
            'limitations': ['Near matches require review; no patient identity inference',
                           'Source classes retain different diagnostic definitions'],
            'near_candidates': near}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'datasets/cross_source_audit.json')
    args = parser.parse_args()
    result = compare({'skindisnet': ROOT / 'datasets/kaggle/skindisnet_3_v1/audit/image_index.jsonl',
                      'scin': ROOT / 'datasets/scin/expansion_audit/image_index.jsonl'})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'near_candidates'}, indent=2))
