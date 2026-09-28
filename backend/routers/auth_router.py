from fastapi import APIRouter, Depends, HTTPException

from backend.models import User
from backend.schemas import RegisterRequest, RegisterResponse, UserResponse
from backend.services.auth_service import AuthError, register_or_login, revoke_token
from backend.services.dependencies import get_bearer_token, get_current_user

router = APIRouter(prefix="/api/auth")


@router.post("/register", response_model=RegisterResponse)
async def register(body: RegisterRequest):
    """Admit a tester. Doubles as sign-in: the same username and email that
    registered an account returns the same account."""
    try:
        user, token = await register_or_login(body.username, body.email)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return {"token": token, "username": user.username, "email": user.email}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "email": user.email}


@router.post("/logout")
async def logout(token: str | None = Depends(get_bearer_token)):
    if token:
        await revoke_token(token)
    return {"status": "ok"}
