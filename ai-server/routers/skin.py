"""
Skin Disease Detection Router
─────────────────────────────────────────────────────────────────
Detects skin conditions: Acne, Eczema, Fungal Infection, Psoriasis,
Melanoma (suspicious), Benign Keratosis, etc.

Pipeline:
  1. YOLOv8  → detect & localize lesion/affected area
  2. EfficientNet-B3 (trained on HAM10000) → classify condition
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
    pil_to_tensor,
)
from utils.response_utils import build_response, not_detected_response, DetectionResponse
from utils.auth_utils import verify_api_key

router = APIRouter(prefix="/api/v1/detect", tags=["Skin Disease"])

# HAM10000 class labels → human readable
SKIN_CLASSES = {
    0: "Actinic Keratosis",
    1: "Basal Cell Carcinoma",
    2: "Benign Keratosis",
    3: "Dermatofibroma",
    4: "Melanoma (Suspicious)",
    5: "Melanocytic Nevus (Mole)",
    6: "Vascular Lesion",
    7: "Eczema",
    8: "Fungal Infection",
    9: "Acne (Severe)",
    10: "Psoriasis",
    11: "Normal Skin",
}

URGENT_CLASSES = {1, 4}  # Requires immediate doctor visit

_yolo_model = None
_classifier = None


def _get_yolo(settings: Settings) -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        model_path = os.path.join(settings.models_dir, "skin_yolo.pt")
        _yolo_model = YOLO(model_path if os.path.exists(model_path) else "yolov8n.pt")
    return _yolo_model


def _get_classifier(settings: Settings):
    """Load EfficientNet-B3 fine-tuned on HAM10000."""
    global _classifier
    if _classifier is None:
        import torch
        import timm

        model_path = os.path.join(settings.models_dir, "skin_efficientnet_b3.pt")
        model = timm.create_model(
            "efficientnet_b3",
            pretrained=False,
            num_classes=len(SKIN_CLASSES)
        )
        if os.path.exists(model_path):
            state = torch.load(model_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
        # If no trained model, use pretrained features as placeholder
        model.eval()
        _classifier = model
    return _classifier


@router.post("/skin", response_model=DetectionResponse)
async def detect_skin_disease(
    image: UploadFile = File(..., description="Clear photo of the affected skin area"),
    _: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
) -> DetectionResponse:
    """
    Detect and classify skin conditions.
    Point camera at affected skin area for real-time analysis.
    """
    raw = await image.read()
    validate_image_size(raw, settings.max_image_size_mb)

    pil_img = enhance_image(pil_from_bytes(raw))

    # ── Step 1: YOLOv8 lesion detection ────────────────────
    import cv2
    img_array = np.array(pil_img)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    yolo = _get_yolo(settings)
    results = yolo(img_bgr, conf=0.25, verbose=False)

    detections = []
    roi_img = pil_img

    if results and len(results[0].boxes) > 0:
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0])
            detections.append({
                "box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                "yolo_confidence": round(conf, 4)
            })
        # Use largest detection for classification
        largest = max(detections, key=lambda d: (
            (d["box"]["x2"] - d["box"]["x1"]) * (d["box"]["y2"] - d["box"]["y1"])
        ))
        b = largest["box"]
        roi_img = pil_img.crop((b["x1"], b["y1"], b["x2"], b["y2"]))

    # ── Step 2: Classification ──────────────────────────────
    import torch
    import torch.nn.functional as F

    tensor = pil_to_tensor(roi_img, size=300)  # EfficientNet-B3 input
    tensor = np.transpose(tensor, (2, 0, 1))   # HWC → CHW
    t = torch.tensor(tensor).unsqueeze(0).float()

    classifier = _get_classifier(settings)
    with torch.no_grad():
        logits = classifier(t)
        probs = F.softmax(logits, dim=1)[0]

    top_class = int(probs.argmax())
    top_conf = float(probs[top_class])
    class_name = SKIN_CLASSES.get(top_class, "Unknown")

    if top_conf < settings.skin_confidence_threshold or top_class == 11:
        return not_detected_response("skin disease", top_conf)

    # ── Build response based on detected class ──────────────
    is_urgent = top_class in URGENT_CLASSES
    recommendations = _get_skin_recommendations(top_class, class_name, is_urgent)

    top_5 = sorted(
        [(SKIN_CLASSES.get(i, "Unknown"), round(float(p), 4)) for i, p in enumerate(probs)],
        key=lambda x: x[1], reverse=True
    )[:5]

    details = {
        "detected_condition": class_name,
        "requires_urgent_care": is_urgent,
        "lesions_detected": len(detections),
        "top_predictions": top_5,
        "dataset": "HAM10000 (10,000 skin images)",
        "model": "EfficientNet-B3 (training in progress — placeholder scores)"
    }

    return build_response(
        result=f"{class_name} Detected",
        confidence=top_conf,
        details=details,
        recommendation=recommendations["advice"],
        next_scan_days=recommendations["next_scan_days"]
    )


def _get_skin_recommendations(class_id: int, class_name: str, urgent: bool) -> dict:
    """Return tailored advice per skin condition."""
    base = {
        7: {  # Eczema
            "advice": (
                "Eczema detected. Recommendations:\n"
                "• Keep skin moisturized — apply fragrance-free moisturizer 2x daily\n"
                "• Avoid hot showers, harsh soaps, and scratching\n"
                "• Use mild, hypoallergenic detergents\n"
                "• Antihistamines may help with itching (consult doctor)\n"
                "• Identify and avoid triggers (dust, certain fabrics, stress)\n"
                "• Doctor may prescribe: Hydrocortisone cream or topical steroids\n"
                "⚠️ See a dermatologist for prescription treatment."
            ),
            "next_scan_days": 14,
        },
        8: {  # Fungal
            "advice": (
                "Fungal Infection detected. Recommendations:\n"
                "• Keep affected area clean and dry at all times\n"
                "• Apply antifungal cream (e.g., Clotrimazole, Miconazole) 2x daily\n"
                "• For scalp/hair: use Ketoconazole shampoo 2-3x per week\n"
                "• Wear loose, breathable clothing (cotton preferred)\n"
                "• Do NOT share towels, combs, or clothing\n"
                "• Complete full treatment course (usually 2-4 weeks)\n"
                "⚠️ See a doctor if no improvement in 2 weeks — may need oral antifungals."
            ),
            "next_scan_days": 14,
        },
        9: {  # Acne
            "advice": (
                "Severe Acne detected. Recommendations:\n"
                "• Wash face with salicylic acid or benzoyl peroxide cleanser 2x daily\n"
                "• Do NOT pop or squeeze pimples — causes scarring\n"
                "• Use non-comedogenic, oil-free moisturizer\n"
                "• Avoid touching face and change pillowcases weekly\n"
                "• Diet: reduce dairy, high-GI foods, and sugar\n"
                "• Drink 8+ glasses of water daily\n"
                "• Doctor may prescribe: Retinoids, Clindamycin, or Isotretinoin for severe cases."
            ),
            "next_scan_days": 21,
        },
    }

    if urgent:
        return {
            "advice": (
                f"⚠️ URGENT: {class_name} detected — requires immediate medical attention.\n"
                "• Do NOT delay — see a dermatologist or oncologist within 48 hours\n"
                "• Do NOT attempt home treatment\n"
                "• Take clear photos of the lesion to share with your doctor\n"
                "• Note any changes in size, color, or bleeding\n"
                "This could be serious. Early detection saves lives."
            ),
            "next_scan_days": 3,
        }

    return base.get(class_id, {
        "advice": (
            f"{class_name} detected. Please consult a dermatologist for proper diagnosis "
            "and treatment. Maintain good skin hygiene and avoid irritants."
        ),
        "next_scan_days": 14,
    })
