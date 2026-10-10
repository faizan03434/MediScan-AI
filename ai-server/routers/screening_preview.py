"""Capture pipeline only. Legacy heuristics are deliberately not clinical inference."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from config import get_settings
from utils.auth_utils import verify_api_key
from utils.image_utils import pil_from_bytes, validate_image_size
from utils.response_utils import DetectionResponse

router = APIRouter(prefix="/api/v1/detect", tags=["Research preview"])
MODULES = {"anemia", "skin", "posture", "eye", "wound", "tongue", "retina"}


@router.post("/{module}", response_model=DetectionResponse)
async def capture_preview(module: str, image: UploadFile = File(...),
                          _: str = Depends(verify_api_key)):
    if module not in MODULES:
        raise HTTPException(404, "Unknown scan module")
    settings = get_settings()
    if image.content_type not in settings.allowed_content_types:
        raise HTTPException(415, "Upload a JPEG, PNG or WebP image")
    raw = await image.read(settings.max_image_size_mb * 1024 * 1024 + 1)
    validate_image_size(raw, settings.max_image_size_mb)
    try:
        captured = pil_from_bytes(raw)
    except Exception:
        raise HTTPException(422, "Image could not be decoded")
    return DetectionResponse(
        result="Inconclusive — clinical model not validated",
        confidence=0,
        details={"module": module, "mode": "research_preview",
                 "clinical_inference": False, "width": captured.width,
                 "height": captured.height, "comparison_eligible": False,
                 "expected_image_modality": "fundus" if module == "retina" else "external_photo",
                 "image_modality_verified": False},
        recommendation=("Photo saved for your history. This preview cannot determine disease, "
                        "severity, healing or which medicine is suitable. Review symptoms and any "
                        "prescription with a licensed clinician. Do not delay care while waiting for a rescan."),
        next_scan_days=None,
    )
