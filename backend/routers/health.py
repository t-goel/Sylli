from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    """Simple liveness check."""
    return {"status": "ok"}
