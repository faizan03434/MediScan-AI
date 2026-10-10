"""Reports actual artifacts; never treats research checkpoints as clinical approval."""
import hashlib
import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends
from utils.auth_utils import verify_api_key

ROOT = Path(__file__).resolve().parents[1]
router = APIRouter(prefix='/api/v1/models', tags=['Model readiness'])

def research_skin_status(directory=None):
    directory = directory or ROOT / 'models/research/skin-cnn-v1'
    card, weights = directory / 'model_card.json', directory / 'weights.pt'
    if not card.exists() or not weights.exists():
        return {'status':
        'not_trained'}
    try:
        metadata = json.loads(card.read_text(encoding='utf-8'))
        if hashlib.sha256(weights.read_bytes()).hexdigest() != metadata['checkpoint_sha256']:
            return {'status': 'integrity_failed'}
        test_evaluated = metadata.get('test_evaluated', 'test_balanced_accuracy' in metadata)
        return {'status': 'trained_unvalidated' if test_evaluated else 'trained_validation_only', 'classes': metadata.get('classes', []),
                'clinical_approved': False,
                'commercial_release_allowed': False,
                'source_license': metadata.get('source_license', 'See dataset license'),
                'split_counts': metadata['split_counts'], 'test_evaluated': test_evaluated,
                'test_balanced_accuracy': metadata.get('test_balanced_accuracy') if test_evaluated else None,
                'validation_balanced_accuracy': metadata.get('validation_balanced_accuracy'),
                'validation_dice': metadata.get('validation_dice'),
                'validation_iou': metadata.get('validation_iou'),
                'split_identity': metadata.get('split_identity'),
                'scope': metadata.get('scope'),
                'scoliosis_supported': metadata.get('scoliosis_supported', False),
                'limitations': metadata['limitations']}
    except (OSError, KeyError, ValueError):
        return {'status':
        'invalid_metadata'}

@router.get('/status')
async def status(_: str = Depends(verify_api_key)):
    return {'clinical_inference_enabled': False,
        'modules': {m: {'clinical_approved': False, 'status': 'validation_required'}
                    for m in ['anemia', 'skin', 'posture', 'eye', 'wound', 'tongue', 'retina']},
        'skin_research': research_skin_status(),
        'skin_patient_research': research_skin_status(ROOT / 'models/research/skindisnet-cnn-v2'),
        'skin_transfer_research': research_skin_status(ROOT / 'models/research/skindisnet-mobilenet-v1'),
        'skin_finetuned_research': research_skin_status(ROOT / 'models/research/skindisnet-finetuned-v1'),
        'medical_research': {name: research_skin_status(ROOT / 'models/research' / directory)
            for name, directory in {'anemia_conjunctiva': 'anemia-conjunctiva-pilot-v1',
                'eye_conjunctivitis': 'eye-conjunctivitis-pilot-v1',
                'wound_segmentation': 'wound-segmentation-pilot-v1',
                'wound_unet': 'wound-unet-v1',
                'posture_sitting': 'sitting-posture-pilot-v1',
                'retina': 'retina-fundus-pilot-v1'}.items()},
        'ocr': {'weights_present': all((ROOT / 'models/ocr' / f).exists()
                 for f in ['craft_mlt_25k.pth', 'english_g2.pth']), 'windows_offline_fallback': os.name == 'nt',
                 'scope': 'printed English text; user confirmation required'},
        'prescription_verification': 'requires_clinician_review'}
