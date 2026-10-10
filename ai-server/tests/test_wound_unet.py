import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'training'))
from train_wound_unet_research import WoundUNet, binary_scores  # noqa: E402


class WoundUNetTests(unittest.TestCase):
    def test_overlap_metrics_match_hand_calculation(self):
        pred = torch.tensor([[[[1., 1.], [0., 0.]]]])
        truth = torch.tensor([[[[1., 0.], [1., 0.]]]])
        dice, iou = binary_scores(pred, truth)
        self.assertAlmostEqual(dice.item(), .5, places=6)
        self.assertAlmostEqual(iou.item(), 1 / 3, places=6)

    def test_missing_wound_prediction_is_not_a_perfect_score(self):
        truth = torch.ones(1, 1, 4, 4)
        dice, iou = binary_scores(torch.zeros_like(truth), truth)
        self.assertLess(dice.item(), .000001)
        self.assertLess(iou.item(), .000001)

    def test_encoder_decoder_preserves_spatial_output_and_gradients(self):
        torch.set_num_threads(2)
        model = WoundUNet()
        output = model(torch.zeros(1, 3, 31, 29))
        self.assertEqual(output.shape, (1, 1, 31, 29))
        output.sum().backward()
        self.assertTrue(torch.isfinite(output).all())
        self.assertIsNotNone(model.encoder1[0].weight.grad)
        self.assertIsNotNone(model.output.weight.grad)
