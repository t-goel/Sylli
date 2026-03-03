import json
import os
import boto3

bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

SYSTEM_PROMPT = """You are a university course parser.
Given a course syllabus, extract a structured week-by-week schedule.
You must respond with ONLY valid JSON, no explanation or markdown.
The JSON must follow this exact schema:
{
  "course_name": "string",
  "weeks": [
    {
      "week": 1,
      "topic": "string",
      "readings": ["string"],
      "notes": "string"
    }
  ]
}
If weeks are grouped into units instead, map each unit to its week numbers.
If a field has no data, use an empty string or empty array."""


def parse_syllabus_with_bedrock(pdf_bytes: bytes) -> dict:
    """Send a syllabus PDF to Claude via Bedrock and return a parsed week map."""
    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "document": {
                            "format": "pdf",
                            "name": "syllabus",
                            "source": {"bytes": pdf_bytes},
                        }
                    },
                    {
                        "text": (
                            "Extract the full week-by-week schedule from this syllabus. "
                            "Return only the JSON object as described."
                        )
                    },
                ],
            }
        ],
    )

    raw_text = response["output"]["message"]["content"][0]["text"]
    return json.loads(raw_text)
