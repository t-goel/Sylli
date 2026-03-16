from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from middleware.auth import get_current_user
from services.material_service import upload_material, confirm_material_week, get_presigned_url
from services.dynamo_service import get_material, list_materials_for_user, update_material_embed_status

router = APIRouter()

ALLOWED_EXTENSIONS = (".pdf", ".pptx", ".docx")


@router.post("/materials", tags=["materials"])
async def upload_material_endpoint(
    file: UploadFile = File(...),
    syllabus_id: str = "",  # optional query param for week_map lookup
    user_id: str = Depends(get_current_user),
):
    """Upload a PDF or PPTX material. Returns material_id and AI-suggested week synchronously."""
    filename = file.filename or ""
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only PDF, PPTX, and DOCX files are supported.")

    # Fetch week_map from DynamoDB if syllabus_id provided
    week_map = {}
    if syllabus_id:
        from services.dynamo_service import get_syllabus
        syllabus = get_syllabus(syllabus_id, user_id)
        if syllabus:
            week_map = syllabus.get("week_map", {})

    try:
        result = await upload_material(file, user_id=user_id, week_map=week_map)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to upload material. Please try again.")


@router.post("/materials/{material_id}/confirm", tags=["materials"])
async def confirm_week_endpoint(
    material_id: str,
    week_number: int = Body(..., embed=True),
    user_id: str = Depends(get_current_user),
):
    """Confirm or override the AI-suggested week. Triggers async embedding."""
    result = confirm_material_week(material_id, user_id, week_number)
    if result is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    # Update DynamoDB embed_status to 'processing' so polling reflects it immediately
    update_material_embed_status(material_id, "processing")
    return result


@router.get("/materials", tags=["materials"])
async def list_materials_endpoint(user_id: str = Depends(get_current_user)):
    """List all materials for the authenticated user, ordered by upload time."""
    items = list_materials_for_user(user_id)
    return {"materials": items}


@router.get("/materials/{material_id}/status", tags=["materials"])
async def get_material_status(material_id: str, user_id: str = Depends(get_current_user)):
    """Return embed_status for the given material. Used for frontend polling."""
    item = get_material(material_id, user_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return {"embed_status": item.get("embed_status", "pending")}


@router.get("/materials/{material_id}/view", tags=["materials"])
async def view_material_endpoint(material_id: str, user_id: str = Depends(get_current_user)):
    """Generate a fresh presigned S3 URL for direct file viewing in the browser."""
    url = get_presigned_url(material_id, user_id)
    if url is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return {"url": url}
