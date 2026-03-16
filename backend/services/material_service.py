import io
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.config import Config

from services.dynamo_service import store_material, get_material, update_material_week, update_material_embed_status, delete_material as _delete_material_record
from services.bedrock_service import MODEL_ID

MATERIALS_BUCKET = os.getenv("MATERIALS_BUCKET", "sylli-materials-bucket")
EMBED_FUNCTION_NAME = os.getenv("EMBED_FUNCTION_NAME", "")

s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
lambda_client = boto3.client("lambda")


def suggest_week_for_material(filename: str, week_map: dict) -> int:
    """Ask Claude which week number best matches this filename. Returns int week number."""
    weeks_summary = "\n".join(
        f"Week {w['week']}: {w['topic']}" for w in week_map.get("weeks", [])
    )
    if not weeks_summary:
        return 1  # fallback if no weeks
    prompt = (
        f"Given this course week schedule:\n{weeks_summary}\n\n"
        f"Which week number does the file '{filename}' most likely belong to? "
        f"Reply with ONLY the integer week number, nothing else."
    )
    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
        raw = response["output"]["message"]["content"][0]["text"].strip()
        return int(raw)
    except Exception:
        # Fallback to week 1 on any error — do not crash the upload
        return 1


async def upload_material(file, user_id: str, week_map: dict) -> dict:
    """Upload material to S3, get AI week suggestion, store DynamoDB record."""
    filename = file.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    file_type = ext if ext in ("pdf", "pptx", "docx") else "pdf"

    material_id = str(uuid4())
    s3_key = f"materials/{material_id}/{filename}"
    file_bytes = await file.read()

    s3.put_object(Bucket=MATERIALS_BUCKET, Key=s3_key, Body=file_bytes)

    suggested_week = suggest_week_for_material(filename, week_map)

    item = {
        "material_id": material_id,
        "user_id": user_id,
        "filename": filename,
        "s3_key": s3_key,
        "file_type": file_type,
        "week_number": suggested_week,
        "week_confirmed": False,
        "embed_status": "pending",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    store_material(item)

    return {
        "material_id": material_id,
        "filename": filename,
        "file_type": file_type,
        "week_number": suggested_week,
        "week_confirmed": False,
        "embed_status": "pending",
    }


def confirm_material_week(material_id: str, user_id: str, week_number: int) -> dict:
    """Confirm or override week assignment. Triggers async embedding. Returns updated status."""
    item = get_material(material_id, user_id)
    if item is None:
        return None  # Router raises 404

    update_material_week(material_id, week_number, week_confirmed=True)

    # Trigger embedding asynchronously — fire and forget
    invoked = False
    if EMBED_FUNCTION_NAME:
        payload = {"material_id": material_id, "user_id": user_id, "week_number": week_number}
        try:
            lambda_client.invoke(
                FunctionName=EMBED_FUNCTION_NAME,
                InvocationType="Event",
                Payload=json.dumps(payload),
            )
            # Only mark processing if invoke succeeded — keeps local dev polling from looping forever
            update_material_embed_status(material_id, "processing")
            invoked = True
        except Exception:
            pass

    embed_status = "processing" if invoked else "pending"
    return {"material_id": material_id, "embed_status": embed_status}


def delete_material(material_id: str, user_id: str) -> bool:
    """Delete material from S3 (best-effort) and remove DynamoDB record. Returns False if not found/owned."""
    item = get_material(material_id, user_id)
    if item is None:
        return False
    try:
        s3.delete_object(Bucket=MATERIALS_BUCKET, Key=item["s3_key"])
    except Exception:
        pass  # S3 object may already be gone (e.g. bucket cleared manually)
    _delete_material_record(material_id)
    return True


def get_presigned_url(material_id: str, user_id: str) -> str | None:
    """Generate a fresh presigned S3 URL for material viewing. Returns None on ownership mismatch."""
    from services.dynamo_service import get_material as _get
    item = _get(material_id, user_id)
    if item is None:
        return None
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": MATERIALS_BUCKET, "Key": item["s3_key"]},
        ExpiresIn=300,
    )
    return url
