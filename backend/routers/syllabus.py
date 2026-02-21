from fastapi import APIRouter, UploadFile, File, HTTPException
from services.syllabus_service import upload_syllabus_to_s3

router = APIRouter()

@router.post("/syllabus", tags=["syllabus"])
async def upload_syllabus(file: UploadFile = File(...)):
    """Receive a syllabus file and store it in S3."""
    try:
        await upload_syllabus_to_s3(file)
        return {"status": "uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
