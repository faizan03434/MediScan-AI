"""
Standardized response builder for all AI detection endpoints.
"""
from typing import Any
from pydantic import BaseModel


class DetectionResponse(BaseModel):
    result: str
    confidence: float
    details: dict[str, Any] | None = None
    recommendation: str | None = None
    next_scan_days: int | None = None
    disclaimer: str = (
        "This is an AI-assisted screening tool. Results are not a medical diagnosis. "
        "Always consult a licensed doctor before making health decisions."
    )


def build_response(
    result: str,
    confidence: float,
    details: dict | None = None,
    recommendation: str | None = None,
    next_scan_days: int | None = None,
) -> DetectionResponse:
    return DetectionResponse(
        result=result,
        confidence=round(confidence, 4),
        details=details,
        recommendation=recommendation,
        next_scan_days=next_scan_days,
    )


def not_detected_response(scan_type: str, confidence: float) -> DetectionResponse:
    """Return when no abnormality is detected."""
    return DetectionResponse(
        result=f"No significant {scan_type} abnormality detected.",
        confidence=round(confidence, 4),
        recommendation=(
            "Your scan appears normal. Maintain a healthy lifestyle: "
            "drink at least 8 glasses of water daily, sleep 7-8 hours, "
            "and exercise regularly. Rescan in 30 days for monitoring."
        ),
        next_scan_days=30,
    )
