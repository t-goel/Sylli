from fastapi import APIRouter, UploadFile, File, HTTPException
from services.syllabus_service import upload_syllabus_to_s3, fetch_syllabus

router = APIRouter()


@router.post("/syllabus", tags=["syllabus"])
async def upload_syllabus(file: UploadFile = File(...)):
    """Upload a syllabus PDF, parse it with AI, and return the week map."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        result = await upload_syllabus_to_s3(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/syllabus/{syllabus_id}", tags=["syllabus"])
async def get_syllabus(syllabus_id: str):
    """Retrieve a previously parsed syllabus by ID."""
    result = await fetch_syllabus(syllabus_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Syllabus not found.")
    return result
