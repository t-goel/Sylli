# Technology Stack

**Analysis Date:** 2026-03-13

## Languages

**Primary:**
- Python 3.13 - Backend service running on AWS Lambda (ARM64 architecture)

## Runtime

**Environment:**
- AWS Lambda (Serverless) with Python 3.13 runtime
- Architecture: ARM64 (graviton processors)

**Package Manager:**
- pip
- Lockfile: Not present (direct requirements.txt specifications only)

## Frameworks

**Core:**
- FastAPI 0.x - Web framework for building REST API endpoints in `backend/app.py`
- Mangum - ASGI to AWS Lambda adapter for handling HTTP requests

**Web Server (Development):**
- Uvicorn - ASGI development server for local testing

## Key Dependencies

**Critical:**
- `boto3` - AWS SDK for integrating with S3, DynamoDB, Bedrock (Claude), and CloudWatch
- `fastapi` - Modern Python async web framework for API routes
- `mangum` - Converts FastAPI ASGI app to AWS Lambda-compatible handler
- `python-multipart` - Required for FastAPI file upload handling (multipart/form-data parsing)

**Infrastructure:**
- `uvicorn` - Local development server (imported but primarily used with SAM local testing)

## Configuration

**Environment:**
- Environment variables injected via AWS Lambda CloudFormation template (`template.yaml`)
- Key variables:
  - `SYLLABUS_BUCKET` = `sylli-syllabus-bucket` (S3 bucket for file storage)
  - `SYLLABUS_TABLE` = `sylli-syllabus-table` (DynamoDB table for metadata)
  - `AWS_REGION` = `us-east-1` (default in Bedrock client initialization)

**Build:**
- AWS SAM CLI configuration: `samconfig.toml`
- CloudFormation Infrastructure-as-Code: `template.yaml`
- Build settings: Parallel builds enabled, caching enabled
- Local development: Warm containers (EAGER mode)

## Platform Requirements

**Development:**
- Python 3.13 interpreter
- AWS SAM CLI (for building and deploying)
- AWS credentials configured locally (for S3, DynamoDB, Bedrock access)
- Docker (for SAM local testing)

**Production:**
- AWS account with permissions for:
  - Lambda execution
  - S3 bucket operations (read/write)
  - DynamoDB table operations (read/write)
  - Bedrock Claude model invocation
  - API Gateway (implicit)
  - CloudWatch logging
- AWS region: us-east-1

## Infrastructure-as-Code (SAM)

**Resources Defined in `template.yaml`:**
- `HelloWorldFunction` (Lambda) - Entry point: `backend/app.lambda_handler`
- `SyllabusTable` (DynamoDB) - Pay-per-request billing, partition key: `syllabus_id`
- `SyllabusBucket` (S3) - Raw file storage for syllabi and documents
- `ApplicationResourceGroup` + `ApplicationInsightsMonitoring` - CloudWatch monitoring

**Lambda Configuration:**
- Timeout: 30 seconds
- LogFormat: JSON
- Architecture: ARM64

## API Gateway Integration

**Implicit API Gateway created by SAM:**
- Route: `/{proxy+}`
- Method: ANY (all HTTP verbs)
- Base path: `/api/v1` (set via router prefix in `backend/app.py`)
- Endpoint: Managed by CloudFormation, accessible via `HelloWorldApi` output

## Testing Dependencies

**Test Framework:**
- `pytest` - Test runner for unit and integration tests
- `boto3` - AWS SDK for integration test access to CloudFormation
- `requests` - HTTP client for API testing

**Test Structure:**
- Unit tests: `tests/unit/test_handler.py`
- Integration tests: `tests/integration/test_api_gateway.py`

---

*Stack analysis: 2026-03-13*
