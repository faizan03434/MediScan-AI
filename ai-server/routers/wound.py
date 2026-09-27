"""
Wound / Ulcer Measurement Router
─────────────────────────────────────────────────────────────────
Measures wound dimensions and assesses healing stage.

Pipeline:
  1. YOLOv8-Seg → segment wound boundary
  2. OpenCV contour analysis → area and perimeter calculation
  3. Reference object (coin/ruler) OR camera height estimation → real-world size in cm
  4. Color analysis → healing stage (fresh, granulating, infected, healed)
─────────────────────────────────────────────────────────────────
"""
import os
import math
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, Depends
from ultralytics import YOLO
from typing import Optional

from config import get_settings, Settings
from utils.image_utils import pil_from_bytes, validate_image_size
from utils.response_utils import build_response, not_detected_response, DetectionResponse
from utils.auth_utils import verify_api_key

router = APIRouter(prefix="/api/v1/detect", tags=["Wound"])

HEALING_STAGES = {
    "fresh":        ("Fresh/Acute Wound", 0.85, 7),
    "granulating":  ("Healing — Granulation Tissue Present", 0.65, 14),
    "infected":     ("Infected Wound — Urgent Attention Needed", 0.90, 3),
    "chronic":      ("Chronic/Non-Healing Wound", 0.80, 7),
    "healed":       ("Wound Healing Well", 0.90, 30),
}

_yolo_model = None


def _get_yolo(settings: Settings) -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(settings.models_dir, "wound_yolo_seg.pt")
        _yolo_model = YOLO(model_path if os.path.exists(model_path) else "yolov8n-seg.pt")
    return _yolo_model


def _classify_wound_stage(roi_bgr: np.ndarray) -> str:
    """Classify wound healing stage from color analysis."""
    import cv2
    rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
    mean_r = float(rgb[:, :, 0].mean())
    mean_g = float(rgb[:, :, 1].mean())
    mean_b = float(rgb[:, :, 2].mean())

    # Infected: yellowish/greenish pus
    if mean_g > mean_r * 0.8 and mean_g > 100:
        return "infected"
    # Fresh wound: deep red
    if mean_r > 160 and mean_g < 80:
        return "fresh"
    # Granulating: pinkish-red (healing)
    if mean_r > 120 and mean_g > 80 and mean_b > 70:
        return "granulating"
    # Healed: skin tone (light, low contrast)
    brightness = (mean_r + mean_g + mean_b) / 3
    if brightness > 150:
        return "healed"
    return "chronic"


def _estimate_size_cm(
    pixel_area: float,
    pixel_perimeter: float,
    img_w: int,
    img_h: int,
    reference_cm: float = 0.0,
    reference_px: float = 0.0,
) -> dict:
    """
    Estimate real-world wound size.
    If reference object (coin diameter in cm + pixel size) provided, use it.
    Otherwise use heuristic: typical phone photo ~30cm → 1px ≈ 0.03cm at 1000px width.
    """
    if reference_cm > 0 and reference_px > 0:
        px_per_cm = reference_px / reference_cm
    else:
        # Heuristic baseline (works reasonably at ~25-35cm phone distance)
        px_per_cm = img_w / 30.0

    area_cm2 = pixel_area / (px_per_cm ** 2)
    # Approximate longest dimension as sqrt of area * 4/pi (ellipse model)
    diameter_cm = 2 * math.sqrt(area_cm2 / math.pi)

    return {
        "area_cm2": round(area_cm2, 2),
        "estimated_diameter_cm": round(diameter_cm, 2),
        "measurement_method": "reference_object" if reference_cm > 0 else "heuristic_30cm",
        "note": "For accurate measurements, place a coin (2.5cm diameter) next to wound."
    }


@router.post("/wound", response_model=DetectionResponse)
async def measure_wound(
    image: UploadFile = File(..., description="Photo of wound, ideally with a reference object (coin/ruler)"),
    reference_diameter_cm: Optional[float] = Form(None, description="Diameter of reference object in cm (e.g. coin = 2.5)"),
    reference_diameter_px: Optional[float] = Form(None, description="Diameter of reference object in pixels (measure from photo)"),
    _: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
) -> DetectionResponse:
    """
    Measure wound size and assess healing stage.
    For accurate size: include a 2.5cm coin in the photo and provide its pixel diameter.
    """
    raw = await image.read()
    validate_image_size(raw, settings.max_image_size_mb)

    import cv2
    pil_img = pil_from_bytes(raw)
    img_array = np.array(pil_img)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    h, w = img_bgr.shape[:2]

    yolo = _get_yolo(settings)
    results = yolo(img_bgr, conf=0.3, verbose=False)

    mask = None
    pixel_area = 0.0
    pixel_perimeter = 0.0
    wound_roi = img_bgr

    if results and results[0].masks is not None and len(results[0].masks) > 0:
        # Use segmentation mask from YOLOv8-Seg
        mask_data = results[0].masks.data[0].cpu().numpy()
        mask_resized = cv2.resize(mask_data, (w, h))
        binary_mask = (mask_resized > 0.5).astype(np.uint8) * 255

        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            pixel_area = cv2.contourArea(largest)
            pixel_perimeter = cv2.arcLength(largest, True)
            x, y, cw, ch = cv2.boundingRect(largest)
            wound_roi = img_bgr[y:y + ch, x:x + cw]
    else:
        # Fallback: use center region as approximate wound area
        cy, cx = h // 2, w // 2
        r = min(h, w) // 4
        wound_roi = img_bgr[cy - r:cy + r, cx - r:cx + r]
        pixel_area = (2 * r) ** 2
        pixel_perimeter = 8 * r  # Approximate

    if pixel_area < 100:
        return not_detected_response("wound", 0.3)

    stage = _classify_wound_stage(wound_roi)
    stage_label, confidence, next_scan_days = HEALING_STAGES[stage]

    size_info = _estimate_size_cm(
        pixel_area, pixel_perimeter, w, h,
        reference_cm=reference_diameter_cm or 0.0,
        reference_px=reference_diameter_px or 0.0,
    )

    recommendation = _get_wound_advice(stage, size_info["area_cm2"])

    details = {
        "healing_stage": stage,
        "pixel_area": round(pixel_area, 1),
        **size_info,
        "segmentation_used": mask is not None,
    }

    return build_response(
        result=f"{stage_label} | Size: ~{size_info['estimated_diameter_cm']} cm",
        confidence=confidence,
        details=details,
        recommendation=recommendation,
        next_scan_days=next_scan_days,
    )


def _get_wound_advice(stage: str, area_cm2: float) -> str:
    base = {
        "fresh": (
            "Fresh wound. Immediate care:\n"
            "• Clean with saline or clean water — do NOT use hydrogen peroxide on open wounds\n"
            "• Apply antiseptic (Betadine) and sterile dressing\n"
            "• Change dressing every 24-48 hours\n"
            "• Keep wound moist (moist healing is faster than dry)\n"
            "• Take Tetanus booster if not vaccinated in 5 years\n"
            "• If wound is > 2cm or deep — seek emergency care immediately"
        ),
        "granulating": (
            "Wound is healing — granulation tissue visible. Keep up good care:\n"
            "• Continue moist wound dressing (hydrocolloid dressings work best)\n"
            "• Do NOT disturb the granulation tissue\n"
            "• Eat high-protein diet (eggs, meat, lentils) — protein builds tissue\n"
            "• Take Zinc and Vitamin C supplements for faster healing\n"
            "• Keep wound protected from sun and pressure"
        ),
        "infected": (
            "⚠️ INFECTED WOUND — See a doctor immediately.\n"
            "Signs of infection: redness, warmth, swelling, pus, foul smell.\n"
            "• Do NOT attempt to drain at home\n"
            "• Doctor will prescribe antibiotics (Amoxicillin / Flucloxacillin)\n"
            "• Keep wound clean with saline\n"
            "• Monitor for fever — if fever > 38.5°C, go to emergency\n"
            "• Diabetic patients: infected wounds can worsen rapidly — act immediately"
        ),
        "chronic": (
            "Chronic non-healing wound. Advanced care needed:\n"
            "• See a wound care specialist or vascular surgeon\n"
            "• Check for underlying causes: diabetes, poor circulation, pressure\n"
            "• Advanced dressings: Negative Pressure Wound Therapy may be needed\n"
            "• Control blood sugar if diabetic (HbA1c < 7%)\n"
            "• Ensure adequate nutrition: protein, Zinc, Vitamin A & C"
        ),
        "healed": (
            "Wound appears to be healing well!\n"
            "• Apply Vitamin E oil or silicone gel to reduce scarring\n"
            "• Protect from sun (UV darkens scars)\n"
            "• Keep moisturized\n"
            "• If wound was significant, follow up with doctor for final check"
        ),
    }
    advice = base.get(stage, "Clean wound and consult a doctor.")
    if area_cm2 > 10:
        advice += "\n⚠️ Large wound area detected — wound care specialist consultation strongly recommended."
    return advice
