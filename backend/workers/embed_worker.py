import logging
import os

import boto3

from services.dynamo_service import get_material, update_material_embed_status
from services.embedding_service import extract_text, chunk_text, embed_text, write_vectors_to_s3

logger = logging.getLogger(__name__)

MATERIALS_BUCKET = os.getenv("MATERIALS_BUCKET", "sylli-materials-bucket")

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """
    Async embedding worker. Triggered by SylliFunction via InvocationType='Event'.

    Event payload: {"material_id": str, "user_id": str, "week_number": int}

    Always sets embed_status to 'ready' or 'error' — never leaves it as 'processing'
    so the frontend poll can always terminate.
    """
    material_id = event["material_id"]
    user_id = event["user_id"]
    week_number = int(event["week_number"])

    try:
        # 1. Fetch material metadata from DynamoDB
        item = get_material(material_id, user_id)
        if item is None:
            logger.error(
                "Material not found or ownership mismatch",
                extra={"material_id": material_id},
            )
            update_material_embed_status(material_id, "error")
            return

        s3_key = item["s3_key"]
        file_type = item.get("file_type", "pdf")

        # 2. Download file from S3
        response = s3.get_object(Bucket=MATERIALS_BUCKET, Key=s3_key)
        file_bytes = response["Body"].read()

        # 3. Extract text
        text = extract_text(file_bytes, file_type)
        if not text.strip():
            logger.warning(
                "No text extracted from material",
                extra={"material_id": material_id},
            )
            update_material_embed_status(material_id, "ready")  # empty is still valid
            return

        # 4. Chunk text
        chunks = chunk_text(text)

        # 5. Embed each chunk via Titan Embed V2
        embeddings = [embed_text(chunk) for chunk in chunks]

        # 6. Write vectors to S3 Vectors with metadata
        write_vectors_to_s3(material_id, user_id, week_number, chunks, embeddings)

        # 7. Mark as ready
        update_material_embed_status(material_id, "ready")
        logger.info(
            "Embedding complete",
            extra={"material_id": material_id, "chunks": len(chunks)},
        )

    except Exception as e:
        logger.error(
            "Embedding worker failed",
            extra={
                "material_id": material_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        # CRITICAL: always set error status so frontend polling terminates
        update_material_embed_status(material_id, "error")
