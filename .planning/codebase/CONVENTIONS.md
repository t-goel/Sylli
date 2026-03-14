# Coding Conventions

**Analysis Date:** 2026-03-13

## Naming Patterns

**Files:**
- Snake_case for all Python files: `syllabus_service.py`, `bedrock_service.py`, `dynamo_service.py`
- Group related files by function: services in `backend/services/`, routers in `backend/routers/`
- File names match module purpose: `*_service.py` for business logic, `*_router.py` pattern not used but implied by router modules

**Functions:**
- Snake_case for all function names: `parse_syllabus_with_bedrock()`, `store_syllabus()`, `get_syllabus()`, `upload_syllabus_to_s3()`
- Async functions use `async def` prefix: `async def upload_syllabus()`, `async def fetch_syllabus()`
- Descriptive names that indicate action and target: `parse_syllabus_with_bedrock()`, `upload_syllabus_to_s3()`, `fetch_syllabus()`

**Variables:**
- Snake_case for all variable names: `syllabus_id`, `s3_key`, `pdf_bytes`, `week_map`, `uploaded_at`
- Constants in UPPER_CASE: `BUCKET_NAME`, `TABLE_NAME`, `MODEL_ID`, `SYSTEM_PROMPT`
- AWS client names use service name pattern: `bedrock` (boto3 client), `dynamodb` (boto3 resource), `s3` (boto3 client)

**Types:**
- Use Python 3.10+ union type syntax: `dict | None` instead of `Optional[dict]`
- Always include type hints for function parameters and return types: `async def fetch_syllabus(syllabus_id: str) -> dict | None:`
- Use built-in types for clarity: `str`, `dict`, `bytes`, `list` for collections

## Code Style

**Formatting:**
- No explicit linting tool configured (no .eslintrc, .flake8, or pyproject.toml found)
- Follows standard Python conventions with 4-space indentation (default Python style)
- Line length appears to follow Python default conventions (80-100 characters)

**Linting:**
- Not explicitly configured in this codebase
- Manual adherence to PEP 8 style conventions observed

## Import Organization

**Order:**
1. Standard library imports: `import json`, `import os`, `import uuid`, `from datetime import datetime, timezone`
2. Third-party imports: `import boto3`, `from fastapi import ...`
3. Local imports: `from services.syllabus_service import ...`, `from routers import health, syllabus`

**Path Aliases:**
- Relative imports from local packages: `from services.syllabus_service import ...`, `from routers import ...`
- No alias imports observed (no `import X as Y` patterns)

## Error Handling

**Patterns:**
- Use FastAPI HTTPException for route-level errors: `raise HTTPException(status_code=400, detail="Only PDF files are supported.")`
- Catch-all exception handling in routers: `except Exception as e: raise HTTPException(status_code=500, detail=str(e))`
- Input validation at route layer before calling service: Check file extension in router before passing to service
- Services raise exceptions naturally (no custom exception handling in services layer)

## Logging

**Framework:** Not explicitly used; no logging imports found in codebase

**Patterns:**
- Logging not currently implemented; relies on print statements and AWS Lambda/CloudWatch for observability
- Consider adding logging for debugging: `import logging` and `logger.info()` for service operations

## Comments

**When to Comment:**
- Docstrings provided for all functions with description of purpose: `"""Upload syllabus to S3, parse it with Bedrock, store result in DynamoDB."""`
- Comments explain complex business logic: In bedrock_service.py, SYSTEM_PROMPT explains expected JSON schema for Claude
- Comments minimal; code is self-documenting through function names

**JSDoc/TSDoc:**
- Uses Python docstrings with triple quotes: `"""Function description."""`
- Docstrings describe parameters and behavior but not in formal format: `"""Upload a syllabus PDF, parse it with AI, and return the week map."""`
- AWS Lambda function includes AWS-specific docstring format in `hello_world/app.py` with Parameters and Returns sections

## Function Design

**Size:** Functions are small and focused:
- `upload_syllabus_to_s3()`: 23 lines with clear three-step process
- `parse_syllabus_with_bedrock()`: 26 lines with single API call
- Most functions: 10-25 lines, single responsibility

**Parameters:**
- Use explicit typed parameters: `file: UploadFile`, `syllabus_id: str`
- Annotate all parameters with types
- Default values for FastAPI route parameters: `file: UploadFile = File(...)`

**Return Values:**
- Always annotated with type hint: `-> dict`, `-> dict | None`, `-> None`
- Return dict for complex data: `{"syllabus_id": syllabus_id, "week_map": week_map}`
- Return None when optional: `-> dict | None` for fetch operations that may not find a result

## Module Design

**Exports:**
- Routers export `router` object: `router = APIRouter()` in each router module
- Services export functions directly for use in other modules
- No `__all__` declarations found; all top-level functions are importable

**Barrel Files:**
- `backend/routers/__init__.py` exists but imports not shown; routers imported individually in main app
- `backend/services/` directory has no barrel file; services imported directly by function name
- No barrel file pattern for re-exporting; direct imports from modules

---

*Convention analysis: 2026-03-13*
