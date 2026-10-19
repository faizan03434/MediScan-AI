"""Per-process bound on expensive image work; reject instead of queuing photos."""
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from fastapi import HTTPException

_slots = BoundedSemaphore(2)


@asynccontextmanager
async def image_slot():
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'Image processing is busy; retry shortly.')
    try:
        yield
    finally:
        _slots.release()
