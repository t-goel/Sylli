import os
import uuid
from datetime import datetime, timezone, timedelta

import jwt
from passlib.context import CryptContext

from services.dynamo_service import store_user, get_user_by_username

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


async def register_user(username: str, pin: str) -> str:
    """Register a new user. Raises ValueError if username is taken or inputs invalid. Returns JWT."""
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not (4 <= len(pin) <= 8) or not pin.isdigit():
        raise ValueError("PIN must be 4-8 digits")
    existing = get_user_by_username(username)
    if existing:
        raise ValueError("Username already taken")
    user_id = str(uuid.uuid4())
    hashed_pin = pwd_context.hash(pin)
    store_user(username=username, user_id=user_id, hashed_pin=hashed_pin)
    return _create_token(user_id, username)


async def login_user(username: str, pin: str) -> str | None:
    """Verify credentials. Returns JWT on success, None on failure."""
    user = get_user_by_username(username)
    if not user or not pwd_context.verify(pin, user["hashed_pin"]):
        return None
    return _create_token(user["user_id"], username)


def _create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
