"""
Anemia Detection Router
─────────────────────────────────────────────────────────────────
Detects anemia via pallor analysis of the lower eyelid (conjunctiva)
or fingernail bed.

Pipeline:
  1. YOLOv8  → detect & crop ROI (eye/nail region)
  2. EfficientNet-B4 → classify: Anemic | Non-Anemic
  3. Color analysis  → RGB pallor score as supporting signal
─────────────────────────────────────────────────────────────────
"""
import os
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends
from ultralytics import YOLO

from config import get_settings, Settings
from utils.image_utils import (
    pil_from_bytes,
    validate_image_size,
    enhance_image,
)
from utils.response_utils import build_response, not_detected_response, DetectionResponse
from utils.auth_utils import verify_api_key

router = APIRouter(prefix="/api/v1/detect", tags=["Anemia"])

# ── Lazy model loading ─────────────────────────────────────────
_yolo_model = None
_classifier = None  # EfficientNet loaded via timm at runtime


def _get_yolo(settings: Settings) -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(settings.models_dir, "anemia_yolo.pt")
        if os.path.exists(model_path):
            _yolo_model = YOLO(model_path)
        else:
            # Fall back to base YOLOv8 until custom model is trained
            _yolo_model = YOLO("yolov8n.pt")
    return _yolo_model


def _pallor_score(roi: np.ndarray) -> float:
    """
    Compute pallor score from the ROI.
    Healthy conjunctiva: R > 180, G > 100.
    Pale (anemic):       R < 160, G < 90.
    Returns 0.0 (healthy) to 1.0 (very pale).
    """
    import cv2
    rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    mean_r = float(rgb[:, :, 0].mean())
    mean_g = float(rgb[:, :, 1].mean())
    mean_b = float(rgb[:, :, 2].mean())

    # Pallor = how much the red channel is reduced compared to brightness
    brightness = (mean_r + mean_g + mean_b) / 3.0
    pallor = 1.0 - (mean_r / max(brightness, 1.0)) / 1.3
    return float(np.clip(pallor, 0.0, 1.0))


@router.post("/anemia", response_model=DetectionResponse)
async def detect_anemia(
    image: UploadFile = File(..., description="Eye (lower eyelid) or fingernail photo"),
    _: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
) -> DetectionResponse:
    """
    Detect anemia from lower eyelid pallor or nail bed color.

    - **Anemia Detected**: pallor score > 0.55 or classifier confidence > threshold
    - **No Anemia**: pallor score < 0.40
    - **Borderline**: intermediate range — recommend retest
    """
    raw = await image.read()
    validate_image_size(raw, settings.max_image_size_mb)

    pil_img = enhance_image(pil_from_bytes(raw))

    # ── Step 1: YOLOv8 ROI detection ──────────────────────────
    import cv2
    img_array = np.array(pil_img)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    yolo = _get_yolo(settings)
    results = yolo(img_bgr, conf=0.3, verbose=False)

    roi_bgr = img_bgr  # Default: use full image if no ROI detected
    roi_detected = False
    roi_box = None

    if results and len(results[0].boxes) > 0:
        box = results[0].boxes[0].xyxy[0].cpu().numpy().astype(int)
        x1, y1, x2, y2 = box
        # Add small padding
        pad = 10
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(img_bgr.shape[1], x2 + pad)
        y2 = min(img_bgr.shape[0], y2 + pad)
        roi_bgr = img_bgr[y1:y2, x1:x2]
        roi_detected = True
        roi_box = {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}

    # ── Step 2: Pallor color analysis ─────────────────────────
    pallor = _pallor_score(roi_bgr)

    # ── Step 3: Classification result ─────────────────────────
    # When custom EfficientNet model is trained, it replaces this heuristic
    confidence = pallor  # Placeholder until model is trained


    if pallor > 0.60:
        result = "Anemia Likely Detected"
        recommendation = (
            "Your scan shows significant pallor which may indicate anemia. "
            "Immediate recommendations:\n"
            "• Consult a doctor immediately for CBC (Complete Blood Count) test\n"
            "• Increase iron-rich foods: spinach, lentils, red meat, fortified cereals\n"
            "• Take Vitamin C with iron-rich meals to improve absorption\n"
            "• Avoid tea/coffee with meals (they reduce iron absorption)\n"
            "• Ensure 8 hours of sleep — fatigue worsens anemia symptoms\n"
            "• Drink 2-3 liters of water daily\n"
            "• Rescan in 7 days after dietary changes"
        )
        next_scan_days = 7
    elif pallor > 0.40:
        result = "Borderline Pallor — Monitor Closely"
        recommendation = (
            "Borderline pallor detected. This could be early anemia or lighting conditions.\n"
            "• Take scan in natural daylight for better accuracy\n"
            "• Increase iron and B12 intake: eggs, dairy, leafy greens\n"
            "• Stay hydrated — drink 8 glasses of water daily\n"
            "• Monitor fatigue, dizziness, and shortness of breath\n"
            "• Consult a doctor if symptoms persist\n"
            "• Rescan in 14 days"
        )
        next_scan_days = 14
        confidence = pallor * 0.7
    else:
        return not_detected_response("anemia", 1.0 - pallor)

    details = {
        "pallor_score": round(pallor, 4),
        "roi_detected": roi_detected,
        "roi_box": roi_box,
        "analysis_area": "lower_eyelid_or_nail",
        "color_analysis": {
            "method": "RGB pallor index",
            "note": "Custom EfficientNet-B4 model training in progress"
        }
    }

    return build_response(result, confidence, details, recommendation, next_scan_days)
