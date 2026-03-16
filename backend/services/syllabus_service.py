import os
import uuid
from datetime import datetime, timezone

import boto3
from fastapi import UploadFile

from services.bedrock_service import parse_syllabus_with_bedrock
from services.dynamo_service import store_syllabus, get_syllabus

s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("SYLLABUS_BUCKET", "sylli-syllabus-bucket")


async def upload_syllabus_to_s3(file: UploadFile, user_id: str) -> dict:
    """Upload syllabus to S3, parse it with Bedrock, store result in DynamoDB."""
    file_bytes = await file.read()

    # Use user_id as syllabus_id — each user has exactly one active syllabus (upsert replaces it)
    syllabus_id = user_id
    s3_key = f"syllabus/{syllabus_id}/{file.filename}"

    # 1. Store raw file in S3
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_bytes)

    # 2. Parse with Bedrock — detect format from filename
    fmt = "docx" if file.filename.lower().endswith(".docx") else "pdf"
    week_map = parse_syllabus_with_bedrock(file_bytes, fmt=fmt)

    # 3. Persist parsed map in DynamoDB
    uploaded_at = datetime.now(timezone.utc).isoformat()
    store_syllabus(
        syllabus_id=syllabus_id,
        filename=file.filename,
        s3_key=s3_key,
        week_map=week_map,
        uploaded_at=uploaded_at,
        user_id=user_id,
    )

    return {"syllabus_id": syllabus_id, "week_map": week_map}


async def fetch_syllabus(syllabus_id: str, user_id: str) -> dict | None:
    """Retrieve a previously parsed syllabus by ID, scoped to the requesting user."""
    return get_syllabus(syllabus_id, user_id=user_id)
