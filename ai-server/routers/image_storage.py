"""Bounded, metadata-free lossless storage encoding. Does not write patient files."""
import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response
from starlette.concurrency import run_in_threadpool
from utils.auth_utils import verify_api_key
from utils.image_utils import pil_from_bytes
from utils.image_workload import image_slot

router = APIRouter(prefix='/api/v1/images', tags=['Private image storage'])
MAX_INPUT = 10 * 1024 * 1024
MAX_OUTPUT = 15 * 1024 * 1024


class BoundedOutput(io.BytesIO):
    def write(self, data):
        if self.tell() + len(data) > MAX_OUTPUT:
            raise HTTPException(413, 'Normalized photo is too large; upload a smaller image.')
        return super().write(data)


def normalize(raw):
    image = pil_from_bytes(raw)
    with BoundedOutput() as output:
        image.save(output, format='PNG')
        return output.getvalue()


@router.post('/normalize')
async def normalize_upload(image: UploadFile = File(...), _: str = Depends(verify_api_key)):
    if image.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        raise HTTPException(415, 'JPEG, PNG or WebP required')
    raw = await image.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        raise HTTPException(413, 'Photo must be under 10 MB')
    async with image_slot():
        data = await run_in_threadpool(normalize, raw)
    return Response(data, media_type='image/png', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
