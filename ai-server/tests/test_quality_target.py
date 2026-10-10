import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from evaluate_quality_target import assess, wilson_interval  # noqa: E402


class QualityTargetTests(unittest.TestCase):
    def card(self):
        return {'classes': ['A', 'B'], 'test_confusion_matrix': [[1000, 1], [1, 1000]],
                'test_evaluated': True, 'external_test': True,
                'patient_identity_verified': True, 'clinical_ground_truth_reviewed': True}

    def test_high_internal_accuracy_is_insufficient(self):
        card = self.card()
        card['external_test'] = False
        self.assertFalse(assess(card, True)['target_met_in_supplied_evidence'])

    def test_reported_accuracy_cannot_hide_missed_minority_class(self):
        card = self.card()
        card.update(test_balanced_accuracy=.999, test_confusion_matrix=[[10000, 0], [10, 0]])
        result = assess(card, True)
        self.assertFalse(result['target_met_in_supplied_evidence'])
        self.assertEqual(result['metrics']['test_balanced_accuracy'], .5)

    def test_passing_target_never_approves_clinical_deployment(self):
        result = assess(self.card(), True)
        self.assertTrue(result['target_met_in_supplied_evidence'])
        self.assertFalse(result['clinical_approved'])
        self.assertFalse(result['deployment_authorized'])

    def test_validation_dice_is_not_external_test_dice(self):
        card = self.card()
        card.update(architecture='WoundSegmenter', validation_dice=1.)
        self.assertFalse(assess(card, True)['target_met_in_supplied_evidence'])

    def test_invalid_numeric_metrics_fail_closed(self):
        for value in (True, float('nan'), float('inf'), 1.1):
            card = self.card()
            card.update(architecture='WoundSegmenter', test_dice=value)
            self.assertFalse(assess(card, True)['target_met_in_supplied_evidence'])

    def test_checkpoint_integrity_is_required(self):
        self.assertFalse(assess(self.card(), False)['target_met_in_supplied_evidence'])

    def test_tiny_perfect_sample_cannot_establish_target(self):
        card = self.card()
        card['test_confusion_matrix'] = [[24, 0], [0, 22]]
        result = assess(card, True)
        self.assertEqual(result['metrics']['test_balanced_accuracy'], 1.)
        self.assertFalse(result['target_met_in_supplied_evidence'])
        self.assertIn('class_recall_and_specificity_confidence_lower_bounds_must_exceed_97_percent',
                      result['unmet_requirements'])

    def test_wilson_interval_known_boundary(self):
        lower, upper = wilson_interval(100, 100)
        self.assertAlmostEqual(lower, .9630065018)
        self.assertAlmostEqual(upper, 1.)
        self.assertLess(wilson_interval(100, 100, 4)[0], lower)
