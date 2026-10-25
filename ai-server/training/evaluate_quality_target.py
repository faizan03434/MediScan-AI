"""Assess a numerical research target; never approve clinical deployment."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
TARGET = .97


def wilson_interval(successes, trials, comparisons=1):
    """Approximate Wilson bounds; Bonferroni across the tested proportions.

    Requires independent patient observations, not augmented-image counts.
    Formula: https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
    """
    if trials <= 0:
        return [0., 1.]
    z = NormalDist().inv_cdf(1 - .05 / (2 * comparisons))
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)) / denominator
    return [max(0., center - margin), min(1., center + margin)]


def score(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def assess(card, integrity_verified=False, target=TARGET):
    if not score(target) or not 0 < target < 1:
        raise ValueError('Target must be a finite fraction strictly between zero and one')
    label = f'{target * 100:g}'
    reasons = []
    if not integrity_verified:
        reasons.append('checkpoint_integrity_unverified')
    for field in ('test_evaluated', 'external_test', 'patient_identity_verified', 'clinical_ground_truth_reviewed'):
        if card.get(field) is not True:
            reasons.append(field + '_required')
    metrics = {}
    if card.get('architecture') in {'WoundSegmenter', 'WoundUNet'}:
        value = card.get('test_dice')
        metrics['test_dice'] = value if score(value) else None
        if not score(value) or value <= target:
            reasons.append(f'external_test_dice_must_exceed_{label}_percent')
    else:
        matrix = card.get('test_confusion_matrix')
        classes = card.get('classes', [])
        valid = (len(classes) >= 2 and isinstance(matrix, list) and len(matrix) == len(classes)
            and all(isinstance(row, list) and len(row) == len(classes) for row in matrix)
            and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for row in matrix for v in row)
            and all(sum(row) > 0 for row in matrix))
        if not valid:
            reasons.append('complete_test_confusion_matrix_required')
        else:
            total = sum(sum(row) for row in matrix)
            recalls, specificities, lower_bounds = [], [], []
            per_class = {}
            for i, name in enumerate(classes):
                tp = matrix[i][i]
                positive = sum(matrix[i])
                negative = total - positive
                fp = sum(matrix[j][i] for j in range(len(classes)) if j != i)
                recall = tp / positive
                specificity = (negative - fp) / negative if negative else 0
                recalls.append(recall)
                specificities.append(specificity)
                recall_interval = wilson_interval(tp, positive, 2 * len(classes))
                specificity_interval = wilson_interval(negative - fp, negative, 2 * len(classes))
                lower_bounds.extend([recall_interval[0], specificity_interval[0]])
                per_class[name] = {'recall': recall, 'specificity': specificity, 'test_examples': positive,
                    'recall_interval': recall_interval, 'specificity_interval': specificity_interval}
            metrics = {'test_balanced_accuracy': sum(recalls) / len(recalls), 'per_class': per_class}
            metrics['interval_method'] = 'Wilson, approximate family 95% coverage, Bonferroni across class recall/specificity; independent patients assumed'
            if metrics['test_balanced_accuracy'] <= target:
                reasons.append(f'test_balanced_accuracy_must_exceed_{label}_percent')
            if min(recalls) <= target or min(specificities) <= target:
                reasons.append(f'every_class_recall_and_specificity_must_exceed_{label}_percent')
            if min(lower_bounds) <= target:
                reasons.append(f'class_recall_and_specificity_confidence_lower_bounds_must_exceed_{label}_percent')
    return {'target': f'>{label}%', 'target_met_in_supplied_evidence': not reasons,
        'clinical_approved': False, 'deployment_authorized': False,
        'metrics': metrics, 'unmet_requirements': reasons,
        'limitation': 'This checks supplied aggregate evidence, not clinical authenticity. Wilson bounds assume independent patients; clustering, site/device bias and segmentation uncertainty require separate review.'}


def main():
    from report_medical_training import MODELS
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=float, default=TARGET)
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'docs/QUALITY_TARGET_RESULTS.json')
    parser.add_argument('--include-experiments', action='store_true')
    args = parser.parse_args()
    if not score(args.target) or not 0 < args.target < 1:
        parser.error('Target must be a finite fraction between zero and one')
    results = {}
    models = dict(MODELS)
    if args.include_experiments:
        models.update({p.name: p.name for p in (ROOT / 'models/research').glob('*20261025') if p.is_dir()})
    for module, directory in models.items():
        root = ROOT / 'models/research' / directory
        if not (root / 'model_card.json').exists():
            results[module] = {'status': 'not_completed', 'clinical_approved': False}
            continue
        card = json.loads((root / 'model_card.json').read_text())
        weights = root / 'weights.pt'
        valid = weights.exists() and hashlib.sha256(weights.read_bytes()).hexdigest() == card.get('checkpoint_sha256')
        results[module] = assess(card, valid, args.target)
    args.output.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps({name: result.get('target_met_in_supplied_evidence', False) for name, result in results.items()}))


if __name__ == '__main__':
    main()
