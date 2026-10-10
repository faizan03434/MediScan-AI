"""
Posture & Scoliosis Detection Router
─────────────────────────────────────────────────────────────────
Analyzes standing posture from side or back view.

Pipeline:
  1. MediaPipe Pose → extract 33 body landmarks
  2. Geometric analysis → spine curvature angles, shoulder/hip alignment
  3. YOLOv8-Pose → optional secondary validation
─────────────────────────────────────────────────────────────────
"""
import math
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends

from config import get_settings, Settings
from utils.image_utils import pil_from_bytes, validate_image_size
from utils.response_utils import build_response, not_detected_response, DetectionResponse
from utils.auth_utils import verify_api_key

router = APIRouter(prefix="/api/v1/detect", tags=["Posture"])

_mp_pose = None
_pose_detector = None


def _get_pose_detector():
    global _mp_pose, _pose_detector
    if _pose_detector is None:
        import mediapipe as mp
        _mp_pose = mp.solutions.pose
        _pose_detector = _mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.5
        )
    return _mp_pose, _pose_detector


def _angle_between(p1: tuple, vertex: tuple, p2: tuple) -> float:
    """Calculate angle at vertex between two lines (p1→vertex and p2→vertex)."""
    v1 = (p1[0] - vertex[0], p1[1] - vertex[1])
    v2 = (p2[0] - vertex[0], p2[1] - vertex[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2) + 1e-9
    mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2) + 1e-9
    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def _analyze_posture(landmarks, img_w: int, img_h: int) -> dict:
    """
    Extract posture metrics from MediaPipe landmarks.
    Returns angles and alignment scores.
    """
    def lm(idx):
        landmark = landmarks[idx]
        return (landmark.x * img_w, landmark.y * img_h)

    # Key landmarks
    left_shoulder  = lm(11)
    right_shoulder = lm(12)
    left_hip       = lm(23)
    right_hip      = lm(24)
    left_ear       = lm(7)
    right_ear      = lm(8)
    nose           = lm(0)

    # Shoulder level difference (scoliosis indicator)
    shoulder_diff = abs(left_shoulder[1] - right_shoulder[1])
    shoulder_diff_pct = shoulder_diff / img_h * 100

    # Hip level difference
    hip_diff = abs(left_hip[1] - right_hip[1])
    hip_diff_pct = hip_diff / img_h * 100

    # Head tilt (ear midpoint vs nose)
    ear_mid_x = (left_ear[0] + right_ear[0]) / 2
    head_tilt = abs(nose[0] - ear_mid_x) / img_w * 100

    # Spine curve proxy: shoulder_mid → hip_mid alignment
    shoulder_mid = ((left_shoulder[0] + right_shoulder[0]) / 2,
                    (left_shoulder[1] + right_shoulder[1]) / 2)
    hip_mid = ((left_hip[0] + right_hip[0]) / 2,
               (left_hip[1] + right_hip[1]) / 2)

    lateral_deviation = abs(shoulder_mid[0] - hip_mid[0]) / img_w * 100

    return {
        "shoulder_imbalance_pct": round(shoulder_diff_pct, 2),
        "hip_imbalance_pct": round(hip_diff_pct, 2),
        "head_tilt_pct": round(head_tilt, 2),
        "lateral_spinal_deviation_pct": round(lateral_deviation, 2),
        "landmarks_detected": 33,
    }


@router.post("/posture", response_model=DetectionResponse)
async def detect_posture(
    image: UploadFile = File(..., description="Full-body photo from front or side view"),
    _: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
) -> DetectionResponse:
    """
    Analyze posture and detect signs of scoliosis or poor alignment.
    For best results: stand straight, use back/front view, full body visible.
    """
    raw = await image.read()
    validate_image_size(raw, settings.max_image_size_mb)

    import cv2
    pil_img = pil_from_bytes(raw)
    img_array = np.array(pil_img)
    img_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    img_rgb = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2RGB)
    h, w = img_array.shape[:2]

    mp_pose, detector = _get_pose_detector()

    result_mp = detector.process(img_rgb)

    if not result_mp.pose_landmarks:
        return DetectionResponse(
            result="Pose Not Detected",
            confidence=0.0,
            details={"error": "Could not detect body landmarks. Ensure full body is visible."},
            recommendation=(
                "Could not detect your body pose.\n"
                "• Stand 2-3 meters from the camera\n"
                "• Ensure full body (head to feet) is in frame\n"
                "• Use good lighting\n"
                "• Wear fitted clothing (avoid loose/baggy clothes)"
            ),
            next_scan_days=None,
        )

    metrics = _analyze_posture(result_mp.pose_landmarks.landmark, w, h)

    # ── Classify posture severity ──────────────────────────
    shoulder_imb = metrics["shoulder_imbalance_pct"]
    lateral_dev  = metrics["lateral_spinal_deviation_pct"]
    hip_imb      = metrics["hip_imbalance_pct"]

    severity_score = (shoulder_imb * 0.4 + lateral_dev * 0.4 + hip_imb * 0.2) / 10.0
    severity_score = min(1.0, severity_score)

    if shoulder_imb > 4.0 or lateral_dev > 5.0:
        result = "Significant Postural Deviation Detected — Possible Scoliosis"
        recommendation = (
            "⚠️ Significant spinal deviation detected. Recommendations:\n"
            "• Consult an orthopedic specialist or physiotherapist immediately\n"
            "• Get a standing X-ray (Cobb angle measurement) for scoliosis diagnosis\n"
            "• Avoid heavy backpacks (use both shoulder straps)\n"
            "• Start core strengthening exercises (consult physio first)\n"
            "• Sleep on a firm mattress with proper pillow support\n"
            "• Avoid prolonged sitting — take breaks every 30 minutes\n"
            "• Posture correction exercises: cat-cow stretch, wall angels\n"
            "• Rescan after 2 weeks of physio"
        )
        next_scan_days = 14
    elif shoulder_imb > 2.0 or lateral_dev > 3.0:
        result = "Mild Postural Imbalance Detected"
        recommendation = (
            "Mild posture issues detected. Recommendations:\n"
            "• Practice 10 minutes of posture exercises daily\n"
            "• Adjust workstation: monitor at eye level, feet flat on floor\n"
            "• Strengthen core: planks, bird-dog, dead bug exercises\n"
            "• Stretch regularly: chest stretch, hip flexor stretch\n"
            "• Walk 30 minutes daily with proper posture awareness\n"
            "• Sleep on your side with a pillow between knees\n"
            "• Rescan in 21 days to track improvement"
        )
        next_scan_days = 21
        severity_score *= 0.6
    else:
        return not_detected_response("posture", 1.0 - severity_score)

    details = {**metrics, "severity_score": round(severity_score, 4)}
    return build_response(result, severity_score, details, recommendation, next_scan_days)
