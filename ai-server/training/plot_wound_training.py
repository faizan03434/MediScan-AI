"""Export aggregate research learning curves, without patient images or identifiers."""
import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / 'models/research/wound-unet-v1'
    card = json.loads((directory / 'model_card.json').read_text(encoding='utf-8'))
    history = json.loads((directory / 'training_history.json').read_text(encoding='utf-8'))
    baseline = json.loads((ROOT / 'models/research/wound-segmentation-pilot-v1/model_card.json').read_text(encoding='utf-8'))
    figure, axes = plt.subplots(figsize=(9, 5), layout='constrained')
    figure.set_facecolor('white')
    axes.plot([r['epoch'] for r in history], [r['validation_dice'] for r in history],
              color='#14766b', linewidth=2, label='U-Net validation Dice')
    axes.axhline(baseline['validation_dice'], color='#767676', linestyle='--', label='Previous CNN best validation Dice')
    axes.scatter([card['best_epoch']], [card['validation_dice']], color='#14766b', s=45, zorder=4)
    axes.set(xlabel='Epoch', ylabel='Mean per-image Dice (0–1)', ylim=(0, 1),
             title='Wound segmentation — research validation only')
    axes.grid(alpha=.15)
    axes.legend(loc='lower right')
    figure.supxlabel('439 train / 109 validation masks; reused validation cohort; patient IDs unverified; no test masks.', fontsize=9)
    output = ROOT.parent / 'docs/WOUND_TRAINING_CURVE.png'
    figure.savefig(output, dpi=160)
    plt.close(figure)
    print(output)


if __name__ == '__main__':
    main()
