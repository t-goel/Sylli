# Codebase Structure

**Analysis Date:** 2026-03-13

## Directory Layout

```
/Users/tanmaygoel/CS/Sylli/
├── backend/                    # FastAPI Lambda application (active)
│   ├── app.py                  # FastAPI instance and Mangum handler
│   ├── requirements.txt         # Python dependencies
│   ├── routers/                # HTTP route handlers
│   │   ├── __init__.py
│   │   ├── health.py           # /api/v1/health endpoint
│   │   └── syllabus.py         # /api/v1/syllabus endpoints
│   └── services/               # Business logic and AWS integrations
│       ├── bedrock_service.py  # Claude 3.5 Sonnet invocations
│       ├── dynamo_service.py   # DynamoDB operations
│       └── syllabus_service.py # Syllabus upload/retrieval logic
├── tests/                      # Test suites
│   ├── __init__.py
│   ├── requirements.txt
│   ├── unit/                   # Unit tests (legacy)
│   │   ├── __init__.py
│   │   └── test_handler.py     # Tests for hello_world app
│   └── integration/            # Integration tests
│       ├── __init__.py
│       └── test_api_gateway.py # Tests for API Gateway endpoints
├── hello_world/                # Legacy sample handler (unused in current deployment)
│   └── app.py
├── template.yaml               # SAM infrastructure-as-code
├── samconfig.toml              # SAM build configuration
├── README.md                   # Project documentation
├── SPEC.md                     # Product requirements (PRD)
└── .planning/                  # GSD planning documents
    └── codebase/               # Architecture/structure analysis
        ├── ARCHITECTURE.md
        └── STRUCTURE.md
```

## Directory Purposes

**backend/**
- Purpose: Production FastAPI Lambda application
- Contains: HTTP routers, business logic services, requirements
- Key files: `app.py` (entry point), `routers/syllabus.py`, `services/`

**backend/routers/**
- Purpose: HTTP endpoint definitions and request/response handling
- Contains: FastAPI APIRouter instances for distinct domains
- Key files: `syllabus.py` (main API), `health.py` (monitoring)

**backend/services/**
- Purpose: Business logic and AWS service integrations
- Contains: Functions for Bedrock parsing, DynamoDB operations, S3 uploads
- Key files: `syllabus_service.py` (orchestration), `bedrock_service.py` (LLM), `dynamo_service.py` (persistence)

**tests/**
- Purpose: Test suites for Lambda and API Gateway
- Contains: Unit tests and integration tests
- Key files: `unit/test_handler.py` (legacy), `integration/test_api_gateway.py` (SAM-based)

**hello_world/**
- Purpose: Legacy sample Lambda handler (not used in current deployment)
- Contains: Basic response function
- Status: Superseded by `backend/` application

## Key File Locations

**Entry Points:**
- `backend/app.py`: FastAPI instance and Lambda handler (`lambda_handler = Mangum(app)`)
- `template.yaml`: SAM definition; specifies `Handler: app.lambda_handler` pointing to backend/

**Configuration:**
- `template.yaml`: Lambda environment variables (SYLLABUS_BUCKET, SYLLABUS_TABLE), IAM policies, S3/DynamoDB resource definitions
- `samconfig.toml`: Build parameters (Python 3.13, arm64 architecture)
- `backend/requirements.txt`: Minimal dependencies (fastapi, mangum, boto3, etc.)

**Core Logic:**
- `backend/services/syllabus_service.py`: Orchestrates upload flow (S3 → Bedrock → DynamoDB)
- `backend/services/bedrock_service.py`: Claude 3.5 Sonnet invocation with PDF processing
- `backend/services/dynamo_service.py`: DynamoDB table operations
- `backend/routers/syllabus.py`: HTTP endpoints for `/api/v1/syllabus` operations

**Testing:**
- `tests/integration/test_api_gateway.py`: Integration test using boto3 CloudFormation and requests
- `tests/unit/test_handler.py`: Unit test for legacy hello_world handler (unrelated to current backend)

## Naming Conventions

**Files:**
- Snake_case: `syllabus_service.py`, `bedrock_service.py`, `dynamo_service.py`
- Router files by domain: `health.py`, `syllabus.py`
- Test files: `test_*.py` pattern
- Environment config: `template.yaml` (SAM), `samconfig.toml`

**Directories:**
- Plural for groupings: `routers/`, `services/`, `tests/`
- By function: `unit/`, `integration/`
- By resource: `backend/` (where Lambda code lives)

**Functions:**
- Async route handlers: `async def upload_syllabus()`, `async def get_syllabus()`
- Async service functions: `async def upload_syllabus_to_s3()`, `async def fetch_syllabus()`
- Sync AWS integration functions: `def parse_syllabus_with_bedrock()`, `def store_syllabus()`

**Variables:**
- Environment vars: ALL_CAPS (`SYLLABUS_BUCKET`, `SYLLABUS_TABLE`)
- Resource identifiers: `syllabus_id` (string UUID)
- AWS clients: `s3 = boto3.client()`, `dynamodb = boto3.resource()`, `bedrock = boto3.client()`
- Table references: `table = dynamodb.Table(TABLE_NAME)`

## Where to Add New Code

**New Feature (e.g., document upload, chat endpoint):**
- Primary code: `backend/services/{feature}_service.py` (orchestration) + `backend/routers/{feature}.py` (HTTP handler)
- AWS integration: Add boto3 calls to new or existing service
- Example: For document upload feature, create `backend/services/document_service.py` and add routes to `backend/routers/documents.py`

**New Component/Module:**
- Implementation: If service-oriented, place in `backend/services/{name}.py`
- If router/endpoint related, place in `backend/routers/{name}.py`
- Follow async pattern for route handlers, sync for AWS integration functions

**Utilities:**
- Shared helpers: Place in `backend/utils/` (create if needed)
- Error handling: Create `backend/utils/errors.py` for custom exceptions
- Constants/config: Create `backend/config.py` for environment loading and schema validation

**Tests:**
- Unit tests for services: `tests/unit/services/test_{service_name}.py`
- Integration tests for endpoints: `tests/integration/test_{feature_name}.py`
- Mock boto3 clients in unit tests; use actual AWS resources in integration tests (SAM-deployed)

## Special Directories

**backend/__pycache__/**
- Purpose: Python bytecode cache (generated at runtime)
- Generated: Yes
- Committed: No (excluded by .gitignore)

**.aws-sam/**
- Purpose: SAM dependency cache and build artifacts
- Generated: Yes (by `sam build`)
- Committed: No

**.git/**
- Purpose: Version control metadata
- Generated: Yes
- Committed: Yes (by definition)

**.planning/codebase/**
- Purpose: GSD architecture and structure analysis documents
- Generated: By gsd:map-codebase command
- Committed: Yes (as reference for planning/execution)

## Import Organization

**Pattern observed in codebase:**

```python
# Standard library
import os
import uuid
import json
from datetime import datetime, timezone

# Third-party libraries
import boto3
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from mangum import Mangum

# Local imports (relative)
from routers import health, syllabus
from services.syllabus_service import upload_syllabus_to_s3, fetch_syllabus
from services.bedrock_service import parse_syllabus_with_bedrock
from services.dynamo_service import store_syllabus, get_syllabus
```

**Rules:**
- Standard library imports first
- Third-party imports second (aws, fastapi, etc.)
- Local imports last
- No explicit path aliases; imports use relative module paths

---

*Structure analysis: 2026-03-13*
