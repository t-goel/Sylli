from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from services.syllabus_service import upload_syllabus_to_s3, fetch_syllabus
from middleware.auth import get_current_user

router = APIRouter()


@router.post("/syllabus", tags=["syllabus"])
async def upload_syllabus(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Upload a syllabus PDF or DOCX, parse it with AI, and return the week map."""
    if not any(file.filename.lower().endswith(ext) for ext in (".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")
    try:
        result = await upload_syllabus_to_s3(file, user_id=user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to parse syllabus. Please try again.")


@router.get("/syllabus", tags=["syllabus"])
async def get_current_syllabus(user_id: str = Depends(get_current_user)):
    """Retrieve the current user's active syllabus (server-side, no localStorage needed)."""
    result = await fetch_syllabus(user_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No syllabus found.")
    return result


@router.get("/syllabus/{syllabus_id}", tags=["syllabus"])
async def get_syllabus(
    syllabus_id: str,
    user_id: str = Depends(get_current_user),
):
    """Retrieve a previously parsed syllabus by ID."""
    result = await fetch_syllabus(syllabus_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Syllabus not found.")
    return result
