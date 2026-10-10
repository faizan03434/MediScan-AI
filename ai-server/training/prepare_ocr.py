"""Explicitly fetch official EasyOCR weights once; inference never downloads models."""
from pathlib import Path
import socket
import easyocr
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "ocr"

if __name__ == "__main__":
    socket.setdefaulttimeout(30)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    easyocr.Reader(["en"], gpu=False, model_storage_directory=str(MODEL_DIR),
                   download_enabled=True, verbose=False)
    print("Local printed-English OCR models ready:", MODEL_DIR)
