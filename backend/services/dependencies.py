"""Shared FastAPI dependencies for authentication."""
from fastapi import HTTPException, Request

from backend.models import User
from backend.services.auth_service import resolve_token


def get_bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


async def get_current_user(request: Request) -> User:
    """The signed-in user, from the middleware's lookup when it already ran."""
    cached = getattr(request.state, "user", None)
    if cached is not None:
        return cached
    user = await resolve_token(get_bearer_token(request))
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    request.state.user = user
    return user
