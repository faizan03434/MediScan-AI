"""
API key authentication for the AI server.
Only the .NET API should call this server directly.
"""
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import get_settings
from secrets import compare_digest

bearer_scheme = HTTPBearer()


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    settings = get_settings()
    if not settings.api_key or not compare_digest(credentials.credentials.encode('utf-8'), settings.api_key.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return credentials.credentials
