"""Nonclinical framing/quality hints. Only posture has a COCO person detector."""
from pathlib import Path
from threading import Lock
import cv2
import numpy as np

_model = None
_lock = Lock()
WEIGHTS = Path(__file__).resolve().parents[1] / 'yolov8n.pt'


def person_box(image):
    global _model
    if not WEIGHTS.is_file():
        return None, 'unavailable'
    with _lock:
        try:
            if _model is None:
                from ultralytics import YOLO
                _model = YOLO(str(WEIGHTS))
            result = _model.predict(image, classes=[0], conf=.55, imgsz=640,
                                    device='cpu', verbose=False, save=False)[0]
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                return None, 'yolov8n-person'
            # Multiple people must not silently select a patient.
            if len(boxes) != 1:
                return None, 'multiple_people'
            x1, y1, x2, y2 = boxes.xyxyn[0].cpu().tolist()
            return {'x': x1, 'y': y1, 'width': x2-x1, 'height': y2-y1}, 'yolov8n-person'
        except Exception:
            # Missing/incompatible dependencies cannot authorize auto-capture.
            return None, 'unavailable'


def guide(image, module, detector=person_box):
    image = image.copy()
    image.thumbnail((640, 640))
    gray = cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    quality = sharpness >= 35 and 35 <= brightness <= 220
    box, kind = detector(image) if module == 'posture' else (None, 'framing_guide')
    framed = box is not None and box['width'] > .12 and box['height'] > .3
    if module == 'posture':
        framed = framed and box['x'] > .01 and box['y'] > .01 and box['x']+box['width'] < .99 and box['y']+box['height'] < .99
    eligible = quality and (framed if module == 'posture' else True)
    message = 'Hold steady' if eligible else 'Improve lighting and focus'
    if module == 'posture' and not framed:
        message = 'Show one person fully inside the frame'
        if kind == 'unavailable':
            message = 'Person detector unavailable; use manual capture'
        if kind == 'multiple_people':
            message = 'Keep only one person in the frame'
    return {'quality_ok': quality, 'capture_eligible': bool(eligible), 'guidance': message,
            'box': box, 'detector': kind, 'target_verified': bool(framed),
            'signal': cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA).flatten().tolist(),
            'clinical_inference': False, 'preview_stored': False,
            'limitation': 'Capture hints only; no disease, prescription or body-part verification. Quality thresholds are development UX heuristics.'}
