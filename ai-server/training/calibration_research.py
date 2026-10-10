"""Reserved-data temperature scaling and rejection evaluation; never clinical approval."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def validate(logits, labels, allow_unknown=False):
    logits, labels = np.asarray(logits, dtype=float), np.asarray(labels)
    if logits.ndim != 2 or logits.shape[1] < 2 or not len(logits) or not np.isfinite(logits).all():
        raise ValueError('Finite nonempty N x C logits required')
    if labels.shape != (len(logits),) or labels.dtype.kind not in 'iu':
        raise ValueError('Integer class labels required')
    if (labels < (-1 if allow_unknown else 0)).any() or (labels >= logits.shape[1]).any():
        raise ValueError('Label outside supported classes')
    return logits, labels


def probabilities(logits, temperature=1.):
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError('Positive finite temperature required')
    with np.errstate(over='ignore', invalid='ignore'):
        scaled = np.asarray(logits, dtype=float) / temperature
    if not np.isfinite(scaled).all():
        raise ValueError('Scaled logits are not finite')
    scaled -= scaled.max(axis=1, keepdims=True)
    values = np.exp(scaled)
    return values / values.sum(axis=1, keepdims=True)


def metrics(logits, labels, temperature=1., bins=15):
    if not isinstance(bins, int) or isinstance(bins, bool) or bins < 1:
        raise ValueError('Positive integer bin count required')
    logits, labels = validate(logits, labels)
    probs = probabilities(logits, temperature)
    confidence, correct = probs.max(1), probs.argmax(1) == labels
    nll = -np.log(np.clip(probs[np.arange(len(labels)), labels], 1e-300, 1)).mean()
    truth = np.eye(logits.shape[1])[labels]
    brier = np.square(probs - truth).sum(1).mean()
    ece = 0.
    for i in range(bins):
        included = (confidence >= i / bins) & ((confidence < (i + 1) / bins) if i < bins - 1 else confidence <= 1)
        if included.any():
            ece += included.mean() * abs(correct[included].mean() - confidence[included].mean())
    return {'negative_log_likelihood': float(nll), 'multiclass_brier': float(brier),
            'expected_calibration_error': float(ece), 'image_accuracy': float(correct.mean())}


def fit_temperature(logits, labels, subject_ids, previously_used_subjects):
    logits, labels = validate(logits, labels)
    subjects = np.asarray(subject_ids)
    if subjects.shape != labels.shape or subjects.dtype.kind != 'U' or any(not s.strip() or s != s.strip() for s in subjects):
        raise ValueError('Calibration subject identifiers required')
    if any(not isinstance(s, str) or not s.strip() or s != s.strip() for s in previously_used_subjects):
        raise ValueError('Canonical string identifiers required in prior-subject registry')
    if set(subjects.tolist()) & set(previously_used_subjects):
        raise ValueError('Calibration overlaps training, selection or previously inspected test subjects')
    if set(labels.tolist()) != set(range(logits.shape[1])):
        raise ValueError('Calibration lacks supported classes')
    # One observation per subject for this first implementation; avoid pretending visits are independent.
    if len(set(subjects.tolist())) != len(subjects):
        raise ValueError('Aggregate repeated visits per subject before calibration')
    candidates = np.unique(np.append(np.geomspace(.05, 20., 121), 1.))
    temperature = float(min(candidates, key=lambda t: metrics(logits, labels, t)['negative_log_likelihood']))
    return {'temperature': temperature, 'calibration_subjects': len(subjects),
            'before': metrics(logits, labels), 'after': metrics(logits, labels, temperature),
            'clinical_approved': False, 'external_evaluated': False,
            'method': 'reserved-subject temperature grid minimizing NLL; calibration-fit scores are optimistic'}


def rejection_report(logits, labels, temperature, threshold):
    logits, labels = validate(logits, labels, allow_unknown=True)
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Threshold must be in [0,1]')
    probs = probabilities(logits, temperature)
    accepted = probs.max(1) >= threshold
    known, unknown = labels >= 0, labels == -1
    accepted_known = accepted & known
    return {'known_coverage': float(accepted[known].mean()) if known.any() else None,
        'accepted_known_error': float((probs.argmax(1)[accepted_known] != labels[accepted_known]).mean()) if accepted_known.any() else None,
        'unknown_false_accept_rate': float(accepted[unknown].mean()) if unknown.any() else None,
        'unknown_examples': int(unknown.sum()), 'clinical_approved': False,
        'limitation': 'Maximum softmax rejection is only a baseline; confidently wrong unknowns can pass. Independent unknown-condition testing required.'}


def main():
    parser = argparse.ArgumentParser(description='Fit research calibration on an explicitly reserved cohort.')
    parser.add_argument('--input', type=Path, required=True, help='NPZ: logits, labels, subject_ids; no pickle arrays')
    parser.add_argument('--protocol', type=Path, required=True, help='JSON role, checkpoint SHA256 and previously_used_subjects')
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    if protocol.get('role') != 'reserved_calibration' or not isinstance(protocol.get('previously_used_subjects'), list):
        raise ValueError('Reserved calibration protocol and prior-subject registry required')
    digest = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    if protocol.get('checkpoint_sha256') != digest:
        raise ValueError('Checkpoint identity mismatch')
    if args.output.exists():
        raise ValueError('Immutable calibration artifact already exists')
    with np.load(args.input, allow_pickle=False) as data:
        result = fit_temperature(data['logits'], data['labels'], data['subject_ids'], protocol['previously_used_subjects'])
    result.update(checkpoint_sha256=digest, input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
                  protocol_sha256=hashlib.sha256(args.protocol.read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    print('Research calibration artifact saved; no clinical deployment authorized.')


if __name__ == '__main__':
    main()
