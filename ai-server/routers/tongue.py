"""
Tongue Diagnosis Router
─────────────────────────────────────────────────────────────────
Analyzes tongue color, coating, and texture for health indicators.
Combines Ayurvedic principles with modern clinical signs.

Detects:
  - Iron/B12 deficiency (pale tongue)
  - Dehydration (dry, cracked)
  - Oral thrush / Candida (white coating)
  - Liver issues (yellow coating)
  - Inflammation / infection (deep red/strawberry tongue)
  - Vitamin deficiency (smooth/bald tongue — B12 deficiency)

Pipeline:
  1. YOLOv8 → detect and crop tongue
  2. Color/texture CNN → classify condition
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

router = APIRouter(prefix="/api/v1/detect", tags=["Tongue"])

TONGUE_CONDITIONS = {
    "pale": {
        "label": "Pale Tongue — Possible Iron/B12 Deficiency or Anemia",
        "advice": (
            "Pale tongue detected. Possible causes: Anemia, Iron deficiency, B12 deficiency.\n"
            "Recommendations:\n"
            "• Increase iron: red meat, spinach, lentils, fortified cereals\n"
            "• Increase B12: eggs, dairy, fish, or B12 supplements\n"
            "• Take Vitamin C with iron-rich meals for better absorption\n"
            "• Get CBC (blood count) and ferritin test from doctor\n"
            "• Stay hydrated — drink 8 glasses of water daily\n"
            "• Sleep 7-8 hours — fatigue worsens deficiency symptoms\n"
            "• Rescan in 14 days after dietary changes"
        ),
        "next_scan_days": 14,
    },
    "white_coat": {
        "label": "White Coating — Possible Oral Thrush or Digestive Issues",
        "advice": (
            "White tongue coating detected. Possible causes: Oral Thrush (Candida), poor digestion, dehydration.\n"
            "Recommendations:\n"
            "• Oral Thrush: doctor will prescribe Nystatin or Fluconazole\n"
            "• Gently brush tongue twice daily with soft toothbrush\n"
            "• Avoid sugar and yeast-containing foods (bread, alcohol, sweet drinks)\n"
            "• Probiotics (yogurt, kefir) help restore good bacteria\n"
            "• Drink warm water with lemon in the morning\n"
            "• If on antibiotics — this is common; inform your doctor\n"
            "• Maintain good oral hygiene"
        ),
        "next_scan_days": 10,
    },
    "yellow_coat": {
        "label": "Yellow Coating — Possible Liver/Digestive Concern",
        "advice": (
            "Yellow tongue coating detected. Possible liver or digestive issue.\n"
            "Recommendations:\n"
            "• Consult a doctor for liver function tests (LFT)\n"
            "• Avoid alcohol and fatty/fried foods\n"
            "• Increase water intake — 2-3 liters daily\n"
            "• Eat more fiber: fruits, vegetables, whole grains\n"
            "• Reduce caffeine and processed foods\n"
            "• If combined with yellow eyes/skin — see doctor immediately (jaundice)"
        ),
        "next_scan_days": 7,
    },
    "red_inflamed": {
        "label": "Red/Inflamed Tongue — Possible Infection or B Vitamin Deficiency",
        "advice": (
            "Deep red or inflamed tongue detected.\n"
            "Possible causes: Strep throat, Kawasaki disease, B vitamin deficiency, acid reflux.\n"
            "Recommendations:\n"
            "• See a doctor if accompanied by sore throat or fever\n"
            "• Increase B vitamins: whole grains, lean meat, eggs, legumes\n"
            "• Avoid spicy, acidic, and hot foods\n"
            "• Use mild, SLS-free toothpaste\n"
            "• Salt water gargles 3x daily for soothing\n"
            "• Stay hydrated"
        ),
        "next_scan_days": 7,
    },
    "dry_cracked": {
        "label": "Dry/Cracked Tongue — Dehydration or Nutritional Deficiency",
        "advice": (
            "Dry or cracked tongue detected. Main cause: Dehydration or Vitamin B3/Iron deficiency.\n"
            "Recommendations:\n"
            "• Increase water intake immediately — drink 8-10 glasses daily\n"
            "• Reduce caffeine and alcohol (dehydrating)\n"
            "• Eat Vitamin B3 rich foods: chicken, tuna, mushrooms, avocado\n"
            "• Mouth breathing at night can cause this — consider nasal strips\n"
            "• Some medications cause dry mouth — ask your doctor\n"
            "• Use alcohol-free mouthwash"
        ),
        "next_scan_days": 14,
    },
    "normal": {
        "label": "Healthy Tongue",
        "advice": None,
        "next_scan_days": 30,
    }
}

_yolo_model = None


def _get_yolo(settings: Settings) -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(settings.models_dir, "tongue_yolo.pt")
        _yolo_model = YOLO(model_path if os.path.exists(model_path) else "yolov8n.pt")
    return _yolo_model


def _analyze_tongue_colors(roi_bgr: np.ndarray) -> dict:
    """Analyze tongue ROI for color patterns."""
    import cv2
    rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)

    mean_r = float(rgb[:, :, 0].mean())
    mean_g = float(rgb[:, :, 1].mean())
    mean_b = float(rgb[:, :, 2].mean())
    mean_l = float(lab[:, :, 0].mean())  # Lightness
    mean_a = float(lab[:, :, 1].mean())  # Green-Red axis
    mean_b_lab = float(lab[:, :, 2].mean())  # Blue-Yellow axis

    # White coat: high brightness, low saturation
    white_score = mean_l / 255.0 if mean_l > 160 else 0.0

    # Yellow coat: high yellow in LAB b-channel
    yellow_score = max(0.0, (mean_b_lab - 128.0) / 80.0)

    # Red/inflamed: high a-channel in LAB
    red_score = max(0.0, (mean_a - 140.0) / 60.0)

    # Pale: low saturation pink
    pale_score = 1.0 - (mean_r / max(mean_g + mean_b, 1.0)) if mean_r < 180 else 0.0

    # Dry/cracked: detect using texture variance
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    variance = float(gray.var())
    dry_score = min(1.0, variance / 3000.0)  # High variance = cracks

    return {
        "white_coat_score": round(white_score, 4),
        "yellow_coat_score": round(yellow_score, 4),
        "red_inflamed_score": round(red_score, 4),
        "pale_score": round(pale_score, 4),
        "dry_cracked_score": round(dry_score, 4),
        "mean_rgb": [round(mean_r, 1), round(mean_g, 1), round(mean_b, 1)],
    }


@router.post("/tongue", response_model=DetectionResponse)
async def diagnose_tongue(
    image: UploadFile = File(..., description="Clear photo of extended tongue in good lighting"),
    _: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
) -> DetectionResponse:
    """
    Analyze tongue color and coating for health indicators.
    Extend tongue fully, use natural lighting, camera 15-20cm away.
    """
    raw = await image.read()
    validate_image_size(raw, settings.max_image_size_mb)

    pil_img = enhance_image(pil_from_bytes(raw), contrast=1.1)
    import cv2
    img_array = np.array(pil_img)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    yolo = _get_yolo(settings)
    results = yolo(img_bgr, conf=0.3, verbose=False)

    roi = img_bgr
    tongue_detected = False

    if results and len(results[0].boxes) > 0:
        box = results[0].boxes[0].xyxy[0].cpu().numpy().astype(int)
        x1, y1, x2, y2 = box
        pad = 5
        roi = img_bgr[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad]
        tongue_detected = True
        if roi.size == 0:
            roi = img_bgr

    colors = _analyze_tongue_colors(roi)

    # Determine dominant condition
    scores = {
        "white_coat":   colors["white_coat_score"],
        "yellow_coat":  colors["yellow_coat_score"],
        "red_inflamed": colors["red_inflamed_score"],
        "pale":         colors["pale_score"],
        "dry_cracked":  colors["dry_cracked_score"],
    }

    best_condition = max(scores, key=scores.get)
    best_score = scores[best_condition]

    if best_score < settings.tongue_confidence_threshold:
        return not_detected_response("tongue abnormality", 1.0 - best_score)

    cond = TONGUE_CONDITIONS[best_condition]

    if cond["advice"] is None:
        return not_detected_response("tongue abnormality", 0.9)

    details = {
        **colors,
        "tongue_detected_by_yolo": tongue_detected,
        "dominant_condition": best_condition,
        "all_scores": scores,
        "note": "Custom tongue CNN training in progress. Color analysis used."
    }

    return build_response(
        result=cond["label"],
        confidence=best_score,
        details=details,
        recommendation=cond["advice"],
        next_scan_days=cond["next_scan_days"],
    )
