import os
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.getenv("SYLLABUS_TABLE", "sylli-syllabus-table")


def store_syllabus(syllabus_id: str, filename: str, s3_key: str, week_map: dict, uploaded_at: str):
    """Persist a parsed syllabus map to DynamoDB."""
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(
        Item={
            "syllabus_id": syllabus_id,
            "filename": filename,
            "s3_key": s3_key,
            "week_map": week_map,
            "uploaded_at": uploaded_at,
        }
    )


def get_syllabus(syllabus_id: str) -> dict | None:
    """Retrieve a parsed syllabus map from DynamoDB by ID."""
    table = dynamodb.Table(TABLE_NAME)
    result = table.get_item(Key={"syllabus_id": syllabus_id})
    return result.get("Item")
