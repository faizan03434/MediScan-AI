import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from train_feature_research import color_features, select_classifier  # noqa: E402
from train_wound_unet_research import WoundUNet, load_initial, segmentation_loss  # noqa: E402
import expand_scin_research  # noqa: E402
from train_sitting_posture_research import normalize_pose  # noqa: E402
from compare_wound_validation import overlap  # noqa: E402
from evaluate_quality_target import assess  # noqa: E402
from predict_feature_research import numeric_probabilities  # noqa: E402


class ResearchImprovementTests(unittest.TestCase):
    def test_numeric_checkpoint_probabilities_match_fitted_estimator(self):
        x = np.asarray([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
        y = np.asarray([0, 0, 1, 1])
        classifier, _ = select_classifier(x, y, x, y, ['A', 'B'])
        scaler, regression = classifier.steps[0][1], classifier.steps[1][1]
        state = {'scaler_mean': torch.tensor(scaler.mean_), 'scaler_scale': torch.tensor(scaler.scale_),
            'coefficients': torch.tensor(regression.coef_), 'intercept': torch.tensor(regression.intercept_),
            'classes': torch.tensor(regression.classes_)}
        actual = numeric_probabilities(state, torch.tensor(x), 2).numpy()
        np.testing.assert_allclose(actual, classifier.predict_proba(x), atol=1e-8)
        mixed = {**state, 'coefficients': state['coefficients'].float(), 'intercept': state['intercept'].float()}
        np.testing.assert_allclose(numeric_probabilities(mixed, torch.tensor(x).float(), 2).numpy(),
                                   classifier.predict_proba(x), atol=1e-6)
        state['scaler_scale'][0] = 0
        with self.assertRaisesRegex(ValueError, 'invalid numeric'):
            numeric_probabilities(state, torch.tensor(x), 2)
    def test_ninety_percent_target_does_not_turn_validation_into_clinical_acceptance(self):
        result = assess({'validation_balanced_accuracy': 1., 'test_evaluated': False}, True, .9)
        self.assertEqual(result['target'], '>90%')
        self.assertFalse(result['target_met_in_supplied_evidence'])
        self.assertIn('external_test_required', result['unmet_requirements'])
        self.assertFalse(result['deployment_authorized'])
        for invalid in (0, 1, True, float('nan')):
            with self.assertRaises(ValueError):
                assess({}, True, invalid)
    def test_normalized_pose_is_translation_and_scale_invariant(self):
        torch.manual_seed(42)
        values = torch.rand(2, 33, 3)
        baseline = normalize_pose(values.reshape(2, 99))
        shifted = values * 2.5 + torch.tensor([3., -2., 7.])
        torch.testing.assert_close(normalize_pose(shifted.reshape(2, 99)), baseline, atol=1e-5, rtol=1e-5)
        with self.assertRaisesRegex(ValueError, 'degenerate'):
            normalize_pose(torch.zeros(1, 99))

    def test_native_mask_metrics_count_each_original_pixel(self):
        truth = np.asarray([[True, True], [False, False]])
        prediction = np.asarray([[True, False], [True, False]])
        dice, iou = overlap(prediction, truth)
        self.assertAlmostEqual(dice, .5, places=6)
        self.assertAlmostEqual(iou, 1 / 3, places=6)
    def test_scin_expansion_preserves_held_out_cases_and_quarantines_duplicates(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / 'datasets/scin'
                (source / 'images').mkdir(parents=True)
                records = []
                for index, (split, label) in enumerate((s, c) for s in ('train', 'val', 'test') for c in ('Acne', 'Eczema', 'Tinea')):
                    pixels = np.random.default_rng(index).integers(0, 256, (64, 64, 3), dtype=np.uint8)
                    path = source / f'images/{index}.png'
                    Image.fromarray(pixels).save(path)
                    records.append({'case_id': str(index), 'label': label, 'split': split,
                        'path': f'images/{index}.png', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                previous = {'clinical_ready': False, 'records': records}
                manifest_path = source / 'research_manifest.json'
                manifest_path.write_text(json.dumps(previous))
                before = manifest_path.read_bytes()

                def fetch_fixture(url, path):
                    if duplicate:
                        path.write_bytes((source / 'images/8.png').read_bytes())
                    else:
                        Image.fromarray(np.random.default_rng(99).integers(0, 256, (64, 64, 3), dtype=np.uint8)).save(path)

                candidates = [{'case_id': '8', 'label': 'Tinea', 'source': 'unused'},
                    {'case_id': 'new-case', 'label': 'Eczema', 'source': 'https://fixture.invalid/image', 'label_weight': .9}]
                with patch.object(expand_scin_research, 'ROOT', root), \
                     patch.object(expand_scin_research, 'eligible_cases', return_value=candidates), \
                     patch.object(expand_scin_research, 'fetch', side_effect=fetch_fixture) as fetch:
                    output = source / 'new_manifest.json'
                    expand_scin_research.run(output)
                self.assertEqual(fetch.call_count, 1)
                result = json.loads(output.read_text())
                self.assertEqual(result['additional_training_cases'], 0 if duplicate else 1)
                self.assertEqual(manifest_path.read_bytes(), before)
                original_assignments = {r['case_id']: r['split'] for r in records}
                self.assertEqual({r['case_id']: r['split'] for r in result['records'] if r['case_id'] in original_assignments}, original_assignments)
                self.assertFalse(result['clinical_ready'])

    def test_color_descriptor_has_finite_fixed_shape_for_black_and_white(self):
        for color in ('black', 'white'):
            descriptor = color_features(Image.new('RGB', (19, 37), color))
            self.assertEqual(descriptor.shape, (60,))
            self.assertTrue(np.isfinite(descriptor).all())
        self.assertFalse(np.array_equal(color_features(Image.new('RGB', (10, 10), 'black')),
                                       color_features(Image.new('RGB', (10, 10), 'white'))))

    def test_scaling_is_fit_only_on_train_and_grid_is_recorded(self):
        features = np.asarray([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
        targets = np.asarray([0, 0, 1, 1])
        validation = np.asarray([[1000., 0.], [1000., 1.]])
        classifier, report = select_classifier(features, targets, validation, np.asarray([0, 1]), ['A', 'B'])
        np.testing.assert_allclose(classifier.steps[0][1].mean_, [.5, .5])
        self.assertEqual(len(report['candidates']), 4)
        self.assertEqual(np.asarray(report['validation_confusion_matrix']).sum(), 2)

    def test_per_image_loss_has_finite_gradients_for_empty_and_small_masks(self):
        logits = torch.zeros(2, 1, 8, 8, requires_grad=True)
        truth = torch.zeros_like(logits)
        truth[1, :, 1, 1] = 1
        loss = segmentation_loss(logits, truth, per_image=True)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertTrue(torch.isfinite(logits.grad).all())
        self.assertNotEqual(loss.item(), segmentation_loss(logits, truth, per_image=False).item())

    def test_warm_start_rejects_different_data_and_modified_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = WoundUNet()
            torch.save(model.state_dict(), root / 'weights.pt')
            digest = hashlib.sha256((root / 'weights.pt').read_bytes()).hexdigest()
            (root / 'model_card.json').write_text(json.dumps({'architecture': 'WoundUNet',
                'manifest_sha256': 'expected', 'checkpoint_sha256': digest, 'clinical_approved': False}))
            self.assertEqual(load_initial(model, root, 'expected'), digest)
            with self.assertRaisesRegex(ValueError, 'same audited manifest'):
                load_initial(model, root, 'different')
            (root / 'weights.pt').write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                load_initial(model, root, 'expected')


if __name__ == '__main__':
    unittest.main()
