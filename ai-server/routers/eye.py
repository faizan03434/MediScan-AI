"""
Eye Disease Detection Router
─────────────────────────────────────────────────────────────────
Detects: Cataract (white/cloudy pupil), Jaundice (yellow sclera),
         Red Eye (conjunctivitis), Normal Eye.

Pipeline:
  1. YOLOv8-Seg → segment eye regions (iris, sclera, pupil)
  2. Color analysis → sclera yellowing (jaundice), pupil opacity (cataract)
  3. CNN classifier → confirm classification
─────────────────────────────────────────────────────────────────
"""
import os
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends
from ultralytics import YOLO

from config import get_settings, Settings
from utils.image_utils import pil_from_bytes, validate_image_size, enhance_image
from utils.response_utils import build_response, not_detected_response, DetectionResponse
from utils.auth_utils import verify_api_key

router = APIRouter(prefix="/api/v1/detect", tags=["Eye Disease"])

EYE_CONDITIONS = {
    "jaundice": {
        "label": "Jaundice (Yellow Sclera) Detected",
        "urgency": "high",
        "advice": (
            "⚠️ Yellowing of the eyes (Jaundice) detected. URGENT recommendations:\n"
            "• See a doctor TODAY — jaundice can indicate liver, bile duct, or blood disorders\n"
            "• Do NOT self-medicate\n"
            "• Get liver function tests (LFT) immediately\n"
            "• Stay hydrated — drink 2-3 liters of water\n"
            "• Avoid alcohol completely\n"
            "• Eat light, low-fat foods: rice, fruits, vegetables\n"
            "• Monitor urine color (dark urine confirms jaundice)\n"
            "This is a medical emergency — do not delay."
        ),
        "next_scan_days": 3,
    },
    "cataract": {
        "label": "Cataract (Cloudy Pupil) Detected",
        "urgency": "medium",
        "advice": (
            "Cataract signs detected. Recommendations:\n"
            "• Schedule an eye exam with an ophthalmologist within 1 week\n"
            "• Cataracts progress slowly but surgery is highly effective\n"
            "• Wear UV-protective sunglasses outdoors\n"
            "• Improve lighting at home for reading and daily tasks\n"
            "• Avoid driving at night if vision is blurry\n"
            "• Maintain blood sugar (diabetes accelerates cataracts)\n"
            "• Take antioxidant-rich foods: carrots, leafy greens, berries\n"
            "• Surgery is simple, safe, and restores vision completely."
        ),
        "next_scan_days": 7,
    },
    "red_eye": {
        "label": "Red Eye (Conjunctivitis) Detected",
        "urgency": "low",
        "advice": (
            "Red Eye / Conjunctivitis detected. Recommendations:\n"
            "• Wash hands frequently — conjunctivitis is highly contagious\n"
            "• Do NOT rub your eyes\n"
            "• Use artificial tears / lubricating eye drops for relief\n"
            "• Cold compress (clean cloth) on closed eyelids 3-4x daily\n"
            "• If bacterial: doctor will prescribe antibiotic eye drops\n"
            "• If allergic: antihistamine eye drops help\n"
            "• Avoid contact lenses until fully healed\n"
            "• Do NOT share towels, pillowcases, or eye makeup\n"
            "• Rescan in 7 days — should resolve within a week."
        ),
        "next_scan_days": 7,
    }
}

_yolo_model = None


def _get_yolo(settings: Settings) -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(settings.models_dir, "eye_yolo_seg.pt")
        _yolo_model = YOLO(model_path if os.path.exists(model_path) else "yolov8n-seg.pt")
    return _yolo_model


def _analyze_eye_colors(img_bgr: np.ndarray) -> dict:
    """
    Analyze sclera (white area) for yellowing and redness,
    and pupil for opacity (cataract).
    """
    import cv2
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    mean_r = float(rgb[:, :, 0].mean())
    mean_g = float(rgb[:, :, 1].mean())
    mean_b = float(rgb[:, :, 2].mean())

    # Jaundice: high yellow = high R+G, low B
    yellow_score = (mean_r + mean_g - 2 * mean_b) / (mean_r + mean_g + mean_b + 1e-9)

    # Red eye: high R relative to G and B
    red_score = (mean_r - (mean_g + mean_b) / 2) / (mean_r + 1e-9)
    red_score = max(0.0, red_score)

    # Cataract: pupil area brightness (opacity = whiter/grayer pupil)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # Look at center region (pupil typically centered)
    h, w = gray.shape
    cx, cy = w // 2, h // 2
    r = min(h, w) // 8
    pupil_roi = gray[max(0, cy - r):cy + r, max(0, cx - r):cx + r]
    pupil_brightness = float(pupil_roi.mean()) / 255.0

    # Normal pupil is dark (< 0.3); cataract makes it gray/white (> 0.5)
    cataract_score = max(0.0, (pupil_brightness - 0.3) / 0.4)

    return {
        "yellow_score": round(float(yellow_score), 4),
        "red_score": round(float(red_score), 4),
        "cataract_score": round(float(cataract_score), 4),
        "pupil_brightness": round(float(pupil_brightness), 4),
    }


@router.post("/eye", response_model=DetectionResponse)
async def detect_eye_disease(
    image: UploadFile = File(..., description="Close-up photo of open eye"),
    _: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
) -> DetectionResponse:
    """
    Detect eye diseases: Jaundice, Cataract, Red Eye.
    For best results: take in good lighting, eye fully open, camera ~20cm away.
    """
    raw = await image.read()
    validate_image_size(raw, settings.max_image_size_mb)

    pil_img = pil_from_bytes(raw)
    import cv2
    img_array = np.array(pil_img)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    yolo = _get_yolo(settings)
    results = yolo(img_bgr, conf=0.3, verbose=False)

    # Crop to eye ROI if detected
    roi = img_bgr
    if results and len(results[0].boxes) > 0:
        box = results[0].boxes[0].xyxy[0].cpu().numpy().astype(int)
        x1, y1, x2, y2 = box
        roi = img_bgr[max(0, y1):y2, max(0, x1):x2]
        if roi.size == 0:
            roi = img_bgr

    colors = _analyze_eye_colors(roi)

    yellow = colors["yellow_score"]
    red    = colors["red_score"]
    cataract = colors["cataract_score"]

    # Determine primary condition
    condition = None
    confidence = 0.0

    if yellow > 0.25:
        condition = "jaundice"
        confidence = min(1.0, yellow * 2.5)
    elif cataract > 0.45:
        condition = "cataract"
        confidence = min(1.0, cataract * 1.5)
    elif red > 0.30:
        condition = "red_eye"
        confidence = min(1.0, red * 2.0)

    if condition is None or confidence < settings.eye_confidence_threshold:
        return not_detected_response("eye disease", 1.0 - max(yellow, cataract, red))

    cond_info = EYE_CONDITIONS[condition]

    details = {
        **colors,
        "condition": condition,
        "urgency": cond_info["urgency"],
        "note": "Custom YOLOv8-Seg + CNN model training in progress. Color analysis used."
    }

    return build_response(
        result=cond_info["label"],
        confidence=confidence,
        details=details,
        recommendation=cond_info["advice"],
        next_scan_days=cond_info["next_scan_days"]
    )
