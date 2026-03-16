import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from routers import health, syllabus, auth, materials, tutor, quiz

logger = logging.getLogger(__name__)

app = FastAPI(title="Sylli Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.amplifyapp.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unhandled exceptions return a proper JSON 500 through the
    normal ASGI response path (and therefore through CORSMiddleware) instead of being
    caught by Mangum's HTTPCycle which sends a plain-text 500 without CORS headers."""
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(syllabus.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(materials.router, prefix="/api/v1")
app.include_router(tutor.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")

# Lambda handler for AWS execution
lambda_handler = Mangum(app, api_gateway_base_path="/Prod")
