from fastapi import FastAPI
from mangum import Mangum
from routers import health, syllabus

app = FastAPI(title="Sylli Backend", version="0.1.0")

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(syllabus.router, prefix="/api/v1")

# Lambda handler for AWS execution
lambda_handler = Mangum(app)
