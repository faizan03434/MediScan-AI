from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from utils.auth_utils import verify_api_key
from utils.image_utils import pil_from_bytes
from services.capture_guidance import guide

router = APIRouter(prefix='/api/v1/capture', tags=['Nonclinical capture guidance'])
MODULES = {'anemia', 'skin', 'eye', 'posture', 'wound', 'tongue'}


@router.post('/{module}')
async def capture_guidance(module: str, image: UploadFile = File(...),
                           _: str = Depends(verify_api_key)):
    if module not in MODULES:
        raise HTTPException(404, 'Unsupported capture module')
    if image.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        raise HTTPException(415, 'JPEG, PNG or WebP required')
    raw = await image.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise HTTPException(413, 'Preview must be under 1 MB')
    try:
        picture = pil_from_bytes(raw)
    except Exception:
        raise HTTPException(422, 'Preview could not be decoded')
    return await run_in_threadpool(guide, picture, module)
