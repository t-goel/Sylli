from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from routers import health, syllabus, auth

app = FastAPI(title="Sylli Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.amplifyapp.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(syllabus.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

# Lambda handler for AWS execution
lambda_handler = Mangum(app, api_gateway_base_path="/Prod")
