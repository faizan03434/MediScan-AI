"""Local printed-text OCR. Never classifies a medicine or verifies a prescription."""
from functools import lru_cache
from pathlib import Path
from threading import Lock
import io
import json
import os
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageOps

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "ocr"
_lock = Lock()

def windows_extract(pixels):
    # Built-in Windows OCR is an offline fallback; no image/text enters a shell command.
    with tempfile.TemporaryDirectory(prefix='mediscan-ocr-') as directory:
        path = Path(directory) / 'input.png'
        Image.fromarray(pixels).save(path, format='PNG')
        try:
            result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-File',
                str(Path(__file__).with_name('windows_ocr.ps1')), '-ImagePath', str(path)],
                capture_output=True, timeout=35, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise FileNotFoundError('Local OCR engine timed out') from None
        if result.returncode != 0:
            raise FileNotFoundError('Local English OCR engine unavailable')
        lines = [{'text': str(row['text'])[:500], 'confidence': None, 'box': [], 'needs_review': True}
                 for row in json.loads(result.stdout).get('lines', [])[:100] if str(row['text']).strip()]
    return lines


@lru_cache(maxsize=1)
def reader():
    if not all((MODEL_DIR / filename).exists() for filename in ('craft_mlt_25k.pth', 'english_g2.pth')):
        raise FileNotFoundError('EasyOCR weights are not prepared')
    import easyocr
    import torch
    torch.set_num_threads(4)
    return easyocr.Reader(["en"], gpu=False, model_storage_directory=str(MODEL_DIR),
                          download_enabled=False, verbose=False)


def extract(raw:
    bytes) -> dict:
    with Image.open(io.BytesIO(raw)) as source:
        if source.width * source.height > 20_000_000:
            raise ValueError("image_dimensions_exceeded")
        image = ImageOps.exif_transpose(source)
        image.thumbnail((2048, 2048))
        pixels = np.asarray(image.convert("RGB"))
    with _lock:
        try:
            output = reader().readtext(pixels, detail=1, paragraph=False, workers=0,
                                      batch_size=1, canvas_size=2048)
        except (FileNotFoundError, ModuleNotFoundError):
            if os.name != 'nt':
                raise
            lines = windows_extract(pixels)
            return response(lines, 'windows-media-ocr-en-US')
    height, width = pixels.shape[:2]
    lines = []
    for polygon, text, confidence in output[:100]:
        text = str(text).strip()
        if not text:
            continue
        lines.append({"text": text[:500], "confidence": round(float(confidence), 4),
                      "box": [[round(float(x) / width, 4), round(float(y) / height, 4)] for x, y in polygon],
                      "needs_review": float(confidence) < 0.8})
    return response(lines, 'easyocr-1.7.2-en')

def response(lines, engine):
    return {"text": "\n".join(line["text"] for line in lines), "lines": lines,
            "engine": engine, "status": "requires_confirmation" if lines else "no_text",
            "handwriting_verified": False, "prescription_verified": False,
            "message": "Check every medicine name, strength and form against the original. Printed English text only; handwriting and clinical suitability are not verified."}
