import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
import evaluate_nail_hb_research as evaluation  # noqa: E402


class FrozenHbEvaluationTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'datasets/original/hb_figshare_25867432'
        raw, run = source / 'raw', root / 'run'
        raw.mkdir(parents=True)
        run.mkdir()
        fields = ['PATIENT_ID', 'MEASUREMENT_DATE', 'HB_LEVEL_GperL', 'NAIL_BOUNDING_BOXES', 'SKIN_BOUNDING_BOXES']
        regions = '[[0,0,4,4],[0,4,4,8],[4,0,8,4]]'
        rows, records = [], []
        for index in range(1, 10):
            image_path = raw / f'{index}.jpg'
            Image.new('RGB', (10, 10), (index * 20, 40, 80)).save(image_path)
            subject = hashlib.sha256(('figshare:25867432:' + str(index)).encode()).hexdigest()
            rows.append([str(index), 'synthetic-date', str(100 + index * 10), regions, regions])
            records.append({'subject_pseudonym': subject, 'path': image_path.name,
                'sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(), 'hb_g_dl': 10. + index,
                'split': 'train' if index < 5 else 'val' if index < 7 else 'test', 'near_duplicate_group': subject})
        with (raw / 'metadata.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(fields)
            writer.writerows(rows)
        with zipfile.ZipFile(source / 'data.zip', 'w') as archive:
            for path in raw.iterdir():
                archive.write(path, path.name)
        digest = hashlib.sha256((source / 'data.zip').read_bytes()).hexdigest()
        torch.save({'scaler_mean': torch.zeros(90, dtype=torch.float64), 'scaler_scale': torch.ones(90, dtype=torch.float64),
            'coefficients': torch.zeros(90, dtype=torch.float64), 'intercept': torch.tensor(12.)}, run / 'weights.pt')
        (run / 'model_card.json').write_text(json.dumps({'model': 'synthetic-only', 'architecture': 'SourceBoxColorRidgeRegression',
            'clinical_approved': False, 'checkpoint_sha256': hashlib.sha256((run / 'weights.pt').read_bytes()).hexdigest()}))
        (run / 'private_manifest.json').write_text(json.dumps({'source_sha256': digest,
            'metadata_sha256': hashlib.sha256((raw / 'metadata.csv').read_bytes()).hexdigest(), 'records': records}))
        return run, digest

    def test_frozen_predictions_are_scored_once_without_clinical_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest = self.fixture(root)
            with patch.object(evaluation, 'ROOT', root), patch.object(evaluation, 'SHA256', digest), patch('sys.stdout', new=io.StringIO()):
                evaluation.evaluate(run)
                report = json.loads((run / 'internal_test_report.json').read_text())
                self.assertEqual(report['test_mae_g_dl'], 6.)
                self.assertEqual(report['test_subject_records'], 3)
                self.assertFalse(report['clinical_approved'])
                self.assertFalse(report['parameters_fitted_on_test'])
                self.assertFalse(report['external_test'])
                with self.assertRaisesRegex(ValueError, 'already consumed'):
                    evaluation.evaluate(run)

    def test_changed_reference_or_near_group_overlap_rejects_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest = self.fixture(root)
            path = run / 'private_manifest.json'
            original = json.loads(path.read_text())
            for kind in ('target', 'group'):
                manifest = json.loads(json.dumps(original))
                if kind == 'target':
                    manifest['records'][-1]['hb_g_dl'] = 1.
                else:
                    manifest['records'][-1]['near_duplicate_group'] = manifest['records'][0]['near_duplicate_group']
                path.write_text(json.dumps(manifest))
                with patch.object(evaluation, 'ROOT', root), patch.object(evaluation, 'SHA256', digest), self.subTest(kind=kind), self.assertRaises(ValueError):
                    evaluation.evaluate(run)
                self.assertFalse((run / 'internal_test_report.json').exists())


if __name__ == '__main__':
    unittest.main()
