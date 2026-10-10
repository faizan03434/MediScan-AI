"""
Image preprocessing utilities shared across all detection modules.
"""
import io
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError
from fastapi import HTTPException

MAX_DECODED_PIXELS = 20_000_000
MAX_IMAGE_EDGE = 10_000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def read_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Convert raw bytes to OpenCV BGR image."""
    image = pil_from_bytes(image_bytes)
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def pil_from_bytes(image_bytes: bytes) -> Image.Image:
    """Bound allocation before decoding; normalize orientation and drop metadata."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(status_code=415, detail='Upload a JPEG, PNG or WebP image.')
            width, height = source.size
            if width * height > MAX_DECODED_PIXELS or max(width, height) > MAX_IMAGE_EDGE:
                raise HTTPException(status_code=413, detail='Image resolution is too large. Resize before uploading.')
            if getattr(source, 'n_frames', 1) != 1:
                raise HTTPException(status_code=415, detail='Upload a single still photo, not an animated image.')
            source.load()
            image = ImageOps.exif_transpose(source).convert('RGB')
            image.info.clear()
            return image
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=413, detail='Image resolution is too large. Resize before uploading.') from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise HTTPException(status_code=400, detail='Invalid image format.') from None


def resize_with_padding(img: np.ndarray, target_size: int = 640) -> np.ndarray:
    """
    Resize image to target_size x target_size with letterbox padding.
    Keeps aspect ratio intact — standard for YOLO input.
    """
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_h, new_w = int(h * scale), int(w * scale)
    resized = cv2.resize(img, (new_w, new_h))

    # Pad to square
    top = (target_size - new_h) // 2
    bottom = target_size - new_h - top
    left = (target_size - new_w) // 2
    right = target_size - new_w - left

    padded = cv2.copyMakeBorder(
        resized, top, bottom, left, right,
        cv2.BORDER_CONSTANT, value=(114, 114, 114)
    )
    return padded


def pil_to_tensor(img: Image.Image, size: int = 224) -> np.ndarray:
    """Resize PIL image and normalize to [0,1] float32 array (H,W,C)."""
    img = img.resize((size, size))
    arr = np.array(img, dtype=np.float32) / 255.0
    # ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406])
    std  = np.array([0.229, 0.224, 0.225])
    arr = (arr - mean) / std
    return arr


def enhance_image(img: Image.Image, contrast: float = 1.2, sharpness: float = 1.1) -> Image.Image:
    """Mild enhancement for medical images before inference."""
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def validate_image_size(image_bytes: bytes, max_mb: int = 10) -> None:
    """Raise if image exceeds size limit."""
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_mb:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({size_mb:.1f} MB). Maximum allowed: {max_mb} MB."
        )
