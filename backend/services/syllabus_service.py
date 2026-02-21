import os
import boto3
from fastapi import UploadFile

s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("SYLLABUS_BUCKET", "my-syllabus-bucket")

async def upload_syllabus_to_s3(file: UploadFile):
    """Upload the given file to the configured S3 bucket."""
    content = await file.read()
    s3.put_object(Bucket=BUCKET_NAME, Key=file.filename, Body=content)
