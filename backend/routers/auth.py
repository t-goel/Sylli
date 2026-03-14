from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.auth_service import register_user, login_user

router = APIRouter()


class AuthRequest(BaseModel):
    username: str
    pin: str


@router.post("/auth/register", tags=["auth"])
async def register(body: AuthRequest):
    """Register a new user. Returns JWT token on success."""
    try:
        token = await register_user(body.username, body.pin)
        return {"token": token}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/auth/login", tags=["auth"])
async def login(body: AuthRequest):
    """Log in with username and PIN. Returns JWT token on success."""
    token = await login_user(body.username, body.pin)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid username or PIN")
    return {"token": token}
