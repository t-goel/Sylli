# Architecture

**Analysis Date:** 2026-03-13

## Pattern Overview

**Overall:** Serverless REST API with three-layer separation (routing, business logic, AWS integration)

**Key Characteristics:**
- Stateless Lambda function handler using FastAPI with Mangum adapter
- Service layer abstracts AWS SDK interactions (S3, DynamoDB, Bedrock)
- Router layer handles HTTP endpoints and input validation
- Event-driven processing via AWS API Gateway proxy routes

## Layers

**Router Layer:**
- Purpose: Handle HTTP requests, validate inputs, route to services
- Location: `backend/routers/`
- Contains: FastAPI APIRouter subclasses (`health.py`, `syllabus.py`)
- Depends on: Service layer (syllabus_service)
- Used by: FastAPI app in `backend/app.py`

**Service Layer:**
- Purpose: Encapsulate business logic and AWS integrations
- Location: `backend/services/`
- Contains: Service classes for distinct concerns (syllabus parsing, document storage, database operations)
- Depends on: AWS SDK (boto3), external LLM (Bedrock)
- Used by: Routers and each other

**AWS Integration Layer:**
- Purpose: Direct interaction with AWS services
- Location: Embedded within service classes (`backend/services/*.py`)
- Contains: boto3 clients and resource initializations
- Depends on: AWS credentials via Lambda execution role

## Data Flow

**Syllabus Upload Flow:**

1. Client sends POST to `/api/v1/syllabus` with PDF file (routers/syllabus.py)
2. `upload_syllabus()` validates file type is PDF
3. Calls `upload_syllabus_to_s3()` from services/syllabus_service.py
4. Service layer:
   - Reads file bytes from UploadFile
   - Generates UUID for syllabus_id
   - Uploads raw PDF to S3 at `s3://sylli-syllabus-bucket/syllabus/{syllabus_id}/{filename}`
   - Calls `parse_syllabus_with_bedrock()` to extract week-by-week schedule
   - Stores parsed metadata in DynamoDB table `sylli-syllabus-table` with syllabus_id as partition key
5. Returns JSON response: `{"syllabus_id": string, "week_map": object}`

**Syllabus Retrieval Flow:**

1. Client sends GET to `/api/v1/syllabus/{syllabus_id}`
2. `get_syllabus()` calls `fetch_syllabus()` from services/syllabus_service.py
3. Service layer queries DynamoDB by syllabus_id
4. Returns parsed week_map structure or 404 if not found

**State Management:**
- Raw syllabus PDFs: Stored in S3 at versioned paths
- Parsed metadata: Stored in DynamoDB with syllabus_id as primary key
- No in-memory state; each Lambda invocation is stateless
- Each request creates fresh boto3 clients and DynamoDB table references

## Key Abstractions

**SyllabusService:**
- Purpose: Coordinate file upload, parsing, and persistence
- Examples: `backend/services/syllabus_service.py`
- Pattern: Async function composition calling parse and store functions

**BedrockService:**
- Purpose: Encapsulate Claude 3.5 Sonnet invocations for document parsing
- Examples: `backend/services/bedrock_service.py`
- Pattern: Direct boto3 bedrock-runtime client; returns parsed JSON

**DynamoService:**
- Purpose: Encapsulate DynamoDB CRUD operations
- Examples: `backend/services/dynamo_service.py`
- Pattern: Table operations (put_item, get_item) with explicit key schema

## Entry Points

**Lambda Handler:**
- Location: `backend/app.py` - `lambda_handler = Mangum(app)`
- Triggers: AWS API Gateway proxy integration (any HTTP method to `/{proxy+}`)
- Responsibilities: Converts API Gateway events to FastAPI requests, returns HTTP responses

**FastAPI Application:**
- Location: `backend/app.py` - `app = FastAPI(...)`
- Triggers: Invoked by Mangum adapter on each Lambda execution
- Responsibilities: Router registration, request/response handling

## Error Handling

**Strategy:** Exceptions propagate to routers, which catch and return HTTP errors

**Patterns:**
- File validation: HTTPException(400) if not PDF in routers/syllabus.py
- Service errors: HTTPException(500) with exception string in response body
- No custom exception classes; relies on HTTPException for all error responses
- Bedrock JSON parsing: json.loads() will raise if malformed (unhandled)
- DynamoDB failures: boto3 exceptions surface as 500 errors

## Cross-Cutting Concerns

**Logging:** None implemented; no structured logging framework detected

**Validation:** File extension checks (.pdf) in router layer; input sanitization missing

**Authentication:** None implemented; routes are open endpoints

**Environment Configuration:** Via AWS Lambda environment variables (SYLLABUS_BUCKET, SYLLABUS_TABLE, AWS_REGION)

---

*Architecture analysis: 2026-03-13*
