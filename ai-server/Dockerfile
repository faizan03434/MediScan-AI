# ── Base: Python 3.11 slim ────────────────────────────────────
FROM python:3.11-slim AS base

# System dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python deps ───────────────────────────────────────
COPY requirements.txt .

# CPU-only torch for smaller image (use GPU image for production)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.4.1+cpu torchvision==0.19.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application ──────────────────────────────────────────
COPY . .

# Create models directory
RUN mkdir -p /app/models

# Security: run as non-root
RUN adduser --disabled-password --gecos "" aiuser && \
    chown -R aiuser:aiuser /app
USER aiuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
