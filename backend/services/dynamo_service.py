import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.getenv("SYLLABUS_TABLE", "sylli-syllabus-table")
USERS_TABLE_NAME = os.getenv("USERS_TABLE", "sylli-users-table")


def store_syllabus(syllabus_id: str, filename: str, s3_key: str, week_map: dict, uploaded_at: str, user_id: str):
    """Persist a parsed syllabus map to DynamoDB, scoped to a user."""
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(
        Item={
            "syllabus_id": syllabus_id,
            "user_id": user_id,
            "filename": filename,
            "s3_key": s3_key,
            "week_map": week_map,
            "uploaded_at": uploaded_at,
        }
    )


def get_syllabus(syllabus_id: str, user_id: str) -> dict | None:
    """Retrieve a parsed syllabus. Returns None if not found or owned by another user."""
    table = dynamodb.Table(TABLE_NAME)
    result = table.get_item(Key={"syllabus_id": syllabus_id})
    item = result.get("Item")
    if item is None:
        return None
    if item.get("user_id") != user_id:
        return None  # Return None (not 403) — avoids confirming item existence to wrong user
    return item


def store_user(username: str, user_id: str, hashed_pin: str):
    """Store a new user with conditional write to enforce username uniqueness."""
    table = dynamodb.Table(USERS_TABLE_NAME)
    try:
        table.put_item(
            Item={
                "username": username,
                "user_id": user_id,
                "hashed_pin": hashed_pin,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            ConditionExpression="attribute_not_exists(username)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError("Username already taken")
        raise


def get_user_by_username(username: str) -> dict | None:
    """Retrieve a user record by username. Returns None if not found."""
    table = dynamodb.Table(USERS_TABLE_NAME)
    result = table.get_item(Key={"username": username})
    return result.get("Item")
