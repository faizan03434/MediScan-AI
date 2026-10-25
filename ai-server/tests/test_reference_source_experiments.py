import io
import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from acquire_hb_reference import safe_members  # noqa: E402
from train_tongue_roi_research import forest_probabilities, forest_state, roi_features  # noqa: E402
from train_nail_hb_research import boxes, grouped_splits, hemoglobin_g_dl  # noqa: E402


class ReferenceSourceExperimentsTests(unittest.TestCase):
    def test_near_grouping_preserves_holdouts_and_quarantines_cross_split_clusters(self):
        records = [{'path': p, 'subject_pseudonym': p * 64, 'hb_g_dl': 12.0} for p in 'abcd']
        pairs = [{'left': 'a', 'right': 'b'}, {'left': 'c', 'right': 'd'}]
        retained, quarantined = grouped_splits(records, pairs, {'a': 'train', 'b': 'val', 'c': 'test'})
        self.assertEqual(quarantined, {'a', 'b'})
        self.assertEqual({r['split'] for r in retained}, {'test'})
        self.assertEqual(len({r['near_duplicate_group'] for r in retained}), 1)

    def test_group_assignment_is_independent_of_hb_values_and_input_order(self):
        records = [{'path': p, 'subject_pseudonym': p * 64, 'hb_g_dl': 12.0} for p in 'abcd']
        pairs = [{'left': 'a', 'right': 'b'}, {'left': 'b', 'right': 'c'}]
        first, _ = grouped_splits(records, pairs, {})
        expected = {r['path']: (r['split'], r['near_duplicate_group']) for r in first}
        for row in records:
            row['hb_g_dl'] = 19.0
        second, _ = grouped_splits(list(reversed(records)), pairs, {})
        self.assertEqual(expected, {r['path']: (r['split'], r['near_duplicate_group']) for r in second})

    def test_hb_source_units_are_converted_explicitly_without_diagnosing_anemia(self):
        self.assertAlmostEqual(hemoglobin_g_dl('126'), 12.6)
        for value in ('nan', 'inf', '-100', '0', '126 g/dL'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                hemoglobin_g_dl(value)

    def test_provider_regions_reject_outside_or_ambiguous_coordinates(self):
        self.assertEqual(len(boxes('[[0,0,4,4],[0,4,4,8],[4,0,8,4]]', 10, 10)), 3)
        for value in ('[[0,0,40,4],[0,4,4,8],[4,0,8,4]]', '[[0,0,4,4]]', '__import__("os")', '[[0,0,0,4],[0,4,4,8],[4,0,8,4]]'):
            with self.subTest(value=value), self.assertRaises((ValueError, SyntaxError)):
                boxes(value, 10, 10)

    def test_numeric_forest_matches_original_estimator_probabilities(self):
        features = np.random.default_rng(42).normal(size=(40, 7)).astype(np.float32)
        labels = np.arange(40) % 3
        model = ExtraTreesClassifier(n_estimators=7, max_depth=4, random_state=42).fit(features, labels)
        restored = forest_probabilities(features, forest_state(model))
        np.testing.assert_allclose(restored, model.predict_proba(features), atol=1e-12)

    def test_original_intake_rejects_unsafe_payloads_before_extraction(self):
        for name in ('../outside.csv', '/outside.csv', 'C:/outside.csv', 'photo\\outside.jpg', 'run.exe'):
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, 'w') as output:
                info = zipfile.ZipInfo('placeholder')
                info.filename = name  # Keep a raw backslash: Windows ZipInfo otherwise normalizes it.
                output.writestr(info, b'synthetic')
            with zipfile.ZipFile(payload) as archive, self.subTest(name=name), self.assertRaises(ValueError):
                safe_members(archive)

    def test_source_symlinks_and_case_collisions_are_rejected(self):
        for names in (['photo.jpg', 'PHOTO.jpg'], ['linked.jpg']):
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, 'w') as output:
                for name in names:
                    info = zipfile.ZipInfo(name)
                    if len(names) == 1:
                        info.external_attr = 0o120777 << 16
                    output.writestr(info, b'synthetic')
            with zipfile.ZipFile(payload) as archive, self.assertRaises(ValueError):
                safe_members(archive)

    def test_appearance_features_exclude_background_and_are_finite(self):
        image = np.full((192, 192, 3), 90, dtype=np.uint8)
        polygon = '2 .25 .25 .75 .25 .75 .75 .25 .75'
        before = roi_features(image, polygon, 2)
        image[:35] = 250
        image[:, :35] = 250
        after = roi_features(image, polygon, 2)
        self.assertTrue(np.isfinite(before).all())
        np.testing.assert_array_equal(before, after)

    def test_region_features_refuse_mixed_labels_and_nonpolygons(self):
        image = np.full((192, 192, 3), 90, dtype=np.uint8)
        for annotation in ('1 .5 .5 .4 .4', '1 .2 .2 .8 .2 .8 .8 .2 .8', '2 nan .2 .8 .2 .8 .8 .2 .8', ''):
            with self.subTest(annotation=annotation), self.assertRaises(ValueError):
                roi_features(image, annotation, 2)


if __name__ == '__main__':
    unittest.main()
