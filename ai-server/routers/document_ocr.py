from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from config import get_settings
from utils.auth_utils import verify_api_key
from services.document_ocr import extract

router = APIRouter(prefix="/api/v1/documents", tags=["Local document OCR"])


@router.post("/ocr")
async def read_document(image: UploadFile = File(...), _: str = Depends(verify_api_key)):
    settings = get_settings()
    if image.content_type not in settings.allowed_content_types:
        raise HTTPException(415, "Only JPEG, PNG and WebP images are accepted")
    limit = settings.max_image_size_mb * 1024 * 1024
    raw = await image.read(limit + 1)
    if not raw:
        raise HTTPException(422, "Image is empty")
    if len(raw) > limit:
        raise HTTPException(413, "Image exceeds the upload limit")
    try:
        return await run_in_threadpool(extract, raw)
    except (FileNotFoundError, ModuleNotFoundError):
        raise HTTPException(503, "OCR engine is not ready. Install dependencies and prepare the local OCR models.")
    except ValueError as error:
        if str(error) == "image_dimensions_exceeded":
            raise HTTPException(413, "Image resolution is too large")
        raise HTTPException(422, "Image could not be decoded")
    except (OSError, SyntaxError):
        raise HTTPException(422, "Image could not be decoded")
