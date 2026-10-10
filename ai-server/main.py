"""
MediScan AI Server — FastAPI Application
─────────────────────────────────────────────────────────────────
AI inference engine for all 6 medical detection modules.
Called exclusively by the .NET API gateway.
─────────────────────────────────────────────────────────────────
"""
import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from routers import screening_preview, document_ocr, model_status, capture_guidance

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logger.info("MediScan AI Server starting", version=settings.app_version)

    # Pre-warm models directory check
    import os
    os.makedirs(settings.models_dir, exist_ok=True)
    logger.info("Models directory ready", path=settings.models_dir)

    yield  # App running

    logger.info("MediScan AI Server shutting down")


app = FastAPI(
    title="MediScan AI Inference Server",
    description=(
        "Internal AI inference server for MediScan AI medical detection system. "
        "Provides 6 detection endpoints: Anemia, Skin Disease, Posture, Eye Disease, "
        "Wound Measurement, and Tongue Diagnosis."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.include_router(capture_guidance.router)

# ── CORS ────────────────────────────────────────────────────────
# Only the .NET API should call this; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:5001"],
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Request timing middleware ───────────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Process-Time-Ms"] = f"{duration * 1000:.2f}"
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response

# ── Global exception handler ────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "result": "Error",
            "confidence": 0.0,
            "details": {"error": "Internal server error. Please try again."},
            "recommendation": None,
            "next_scan_days": None,
            "disclaimer": "An error occurred during analysis.",
        }
    )

# ── Routers ─────────────────────────────────────────────────────
app.include_router(screening_preview.router)
app.include_router(document_ocr.router)
app.include_router(model_status.router)

# ── Health & Info endpoints ─────────────────────────────────────
@app.get("/", tags=["Info"])
async def root():
    return {
        "name": "MediScan AI Inference Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "anemia":   "/api/v1/detect/anemia",
            "skin":     "/api/v1/detect/skin",
            "posture":  "/api/v1/detect/posture",
            "eye":      "/api/v1/detect/eye",
            "wound":    "/api/v1/detect/wound",
            "tongue":   "/api/v1/detect/tongue",
        }
    }


@app.get("/health", tags=["Info"])
async def health():
    import torch
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


@app.get("/models/status", tags=["Info"])
async def models_status():
    """Check which trained model files exist."""
    import os
    settings = get_settings()
    model_files = {
        "anemia_yolo":          "anemia_yolo.pt",
        "anemia_classifier":    "anemia_efficientnet_b4.pt",
        "skin_yolo":            "skin_yolo.pt",
        "skin_classifier":      "skin_efficientnet_b3.pt",
        "eye_yolo_seg":         "eye_yolo_seg.pt",
        "wound_yolo_seg":       "wound_yolo_seg.pt",
        "tongue_yolo":          "tongue_yolo.pt",
        "posture_yolo":         "posture_yolo_pose.pt",
    }
    status = {}
    for name, filename in model_files.items():
        path = os.path.join(settings.models_dir, filename)
        status[name] = {
            "exists": os.path.exists(path),
            "path": path,
            "status": "present_unvalidated" if os.path.exists(path) else "not_trained_yet"
        }
    return {"models": status, "clinical_inference_enabled": False, "mode": "research_preview"}
