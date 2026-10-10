"""Export aggregate artifact status; never export image paths or clinical metadata."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = {'skin': 'skindisnet-finetuned-v1', 'anemia_conjunctiva': 'anemia-conjunctiva-pilot-v1',
          'eye_conjunctivitis': 'eye-conjunctivitis-pilot-v1', 'wound_segmentation': 'wound-segmentation-pilot-v1',
          'wound_unet': 'wound-unet-v1',
          'posture_sitting': 'sitting-posture-pilot-v1',
          'retina': 'retina-fundus-pilot-v1'}


def report():
    modules = {}
    for name, run in MODELS.items():
        directory = ROOT / 'models/research' / run
        card, weights = directory / 'model_card.json', directory / 'weights.pt'
        if not card.exists() or not weights.exists():
            modules[name] = {'status': 'not_completed', 'clinical_approved': False}
            continue
        metadata = json.loads(card.read_text(encoding='utf-8'))
        if hashlib.sha256(weights.read_bytes()).hexdigest() != metadata['checkpoint_sha256']:
            modules[name] = {'status': 'integrity_failed', 'clinical_approved': False}
            continue
        keys = ['model', 'architecture', 'classes', 'epochs_completed', 'best_epoch', 'split_counts',
                'split_identity', 'validation_balanced_accuracy', 'test_balanced_accuracy', 'test_roc_auc',
                'validation_dice', 'validation_iou', 'test_evaluated', 'test_report', 'test_confusion_matrix',
                'checkpoint_sha256', 'limitations', 'scope', 'tasks', 'primary_task', 'subject_counts', 'scoliosis_supported']
        modules[name] = {k: metadata[k] for k in keys if k in metadata}
        modules[name].update({'status': 'trained_research_only', 'clinical_approved': False,
                             'commercial_release_allowed': False})
    modules['tongue'] = {'status': 'appearance_candidates_found_access_and_disease_ground_truth_pending', 'clinical_approved': False}
    modules['posture'] = {'status': 'clinical_candidate_found_access_approval_and_scope_review_pending', 'clinical_approved': False}
    output = ROOT.parent / 'docs/MEDICAL_TRAINING_RESULTS.json'
    output.write_text(json.dumps({'modules': modules, 'clinical_inference_enabled': False}, indent=2), encoding='utf-8')
    print(json.dumps({k: v['status'] for k, v in modules.items()}), flush=True)


if __name__ == '__main__':
    report()
