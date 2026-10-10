import unittest
import numpy as np
from training.calibration_research import fit_temperature, metrics, probabilities, rejection_report


class CalibrationTests(unittest.TestCase):
    def test_overconfidence_improves_nll_without_changing_argmax(self):
        logits = np.array([[8., 0.]] * 4 + [[0., 8.]] * 4)
        labels = np.array([0, 0, 0, 1, 1, 1, 1, 0])
        fitted = fit_temperature(logits, labels, [str(i) for i in range(8)], [])
        self.assertGreater(fitted['temperature'], 1)
        self.assertLess(fitted['after']['negative_log_likelihood'], fitted['before']['negative_log_likelihood'])
        np.testing.assert_array_equal(probabilities(logits).argmax(1), probabilities(logits, fitted['temperature']).argmax(1))
        self.assertFalse(fitted['clinical_approved'])

    def test_seen_subjects_and_repeated_visits_rejected(self):
        for subjects, previous in [(['A', 'B'], ['A']), (['A', 'A'], [])]:
            with self.assertRaises(ValueError):
                fit_temperature([[1, 0], [0, 1]], [0, 1], subjects, previous)
        for subjects, previous in [([b'A', b'B'], ['A']), ([' A', 'B'], ['A']), (['A', 'B'], [b'A'])]:
            with self.assertRaises(ValueError):
                fit_temperature([[1, 0], [0, 1]], [0, 1], subjects, previous)

    def test_nan_and_outside_labels_rejected(self):
        for logits, labels in [([[float('nan'), 0]], [0]), ([[1, 0]], [2]), ([[1, 0]], [True])]:
            with self.assertRaises(ValueError):
                metrics(logits, labels)

    def test_no_unknown_data_cannot_claim_unknown_safety(self):
        result = rejection_report([[8., 0.]], [0], 1., .9)
        self.assertIsNone(result['unknown_false_accept_rate'])

    def test_confident_unknown_can_pass_and_is_reported(self):
        result = rejection_report([[8., 0.], [0., 0.]], [-1, -1], 1., .9)
        self.assertEqual(result['unknown_false_accept_rate'], .5)
        self.assertFalse(result['clinical_approved'])
