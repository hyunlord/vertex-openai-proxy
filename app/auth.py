from fastapi import Header, HTTPException, status

from app.config import settings


async def require_internal_bearer_token(
    authorization: str | None = Header(default=None),
) -> None:
    expected = f"Bearer {settings.internal_bearer_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
