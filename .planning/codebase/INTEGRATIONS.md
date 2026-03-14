# External Integrations

**Analysis Date:** 2026-03-13

## APIs & External Services

**Bedrock (Claude Models):**
- Claude 3.5 Sonnet - AI model for syllabus parsing and document analysis
  - SDK/Client: `boto3` (bedrock-runtime)
  - Model ID: `anthropic.claude-3-5-sonnet-20241022-v2:0`
  - Implementation: `backend/services/bedrock_service.py`
  - Methods: `bedrock.converse()` for document analysis with PDF inputs
  - Auth: AWS IAM (Lambda execution role with `bedrock:InvokeModel` permission)

**Bedrock Knowledge Bases (Planned):**
- Embedding model: Amazon Titan Embeddings (via Bedrock Knowledge Bases API)
- Vector store: Amazon OpenSearch Serverless
- Purpose: RAG (Retrieval-Augmented Generation) for tutor chat and quiz generation
- Data source: S3 bucket (`documents/` prefix) with automatic syncing

## Data Storage

**Databases:**
- DynamoDB (AWS managed)
  - Table: `sylli-syllabus-table`
    - Connection: Configured via Lambda IAM role with `DynamoDBReadPolicy` and `DynamoDBWritePolicy`
    - Client: `boto3.resource("dynamodb")` in `backend/services/dynamo_service.py`
    - Primary key: `syllabus_id` (String)
    - Data: Parsed course structure (week maps), metadata (filename, S3 key, upload timestamp)
  - Planned tables:
    - `sylli-documents-table` - Document metadata with GSI on `syllabus_id` and `week`
    - `sylli-conversations-table` - Chat history per syllabus
    - `sylli-quizzes-table` - Quiz definitions and submission records

**File Storage:**
- AWS S3 (sylli-syllabus-bucket)
  - Object layout:
    ```
    syllabus/{syllabus_id}/{filename}.pdf
    documents/{syllabus_id}/{document_id}/{filename}
    ```
  - Client: `boto3.client("s3")` in `backend/services/syllabus_service.py`
  - Operations: `put_object()` for file storage
  - Auth: Lambda IAM role with `S3ReadPolicy` and `S3WritePolicy`

**Caching:**
- None currently implemented
- Bedrock Knowledge Bases will provide embedding-based caching for RAG queries (planned)

## Authentication & Identity

**Auth Provider:**
- AWS IAM - All service-to-service authentication handled by Lambda execution role
- No end-user authentication implemented yet

**Lambda Execution Role (IAM):**
- Policies attached:
  - `S3WritePolicy` on `sylli-syllabus-bucket`
  - `S3ReadPolicy` on `sylli-syllabus-bucket`
  - `DynamoDBWritePolicy` on `sylli-syllabus-table`
  - `DynamoDBReadPolicy` on `sylli-syllabus-table`
  - `bedrock:InvokeModel` on resource `*` (all Bedrock models)

**Future Authentication (Planned):**
- Amazon Cognito User Pools for end-user authentication
- Cognito JWT tokens validated at API Gateway

## Monitoring & Observability

**Error Tracking & Logs:**
- CloudWatch Logs (implicit from Lambda)
  - Log format: JSON
  - Log group: Auto-created by Lambda
- CloudWatch Application Insights:
  - `ApplicationResourceGroup` - Logical grouping of stack resources
  - `ApplicationInsightsMonitoring` - Auto-configured monitoring dashboard
  - Auto-enable: `true` in `template.yaml`

**Metrics:**
- CloudWatch Metrics (implicit from Lambda and DynamoDB)
- No custom metrics implementation yet

## CI/CD & Deployment

**Hosting:**
- AWS Lambda (Serverless) - Full deployment via SAM CloudFormation stack
- Region: `us-east-1`
- Stack name: `Sylli`

**Infrastructure Management:**
- AWS SAM CLI for local development and deployment
- CloudFormation for infrastructure-as-code
- Configuration: `samconfig.toml` and `template.yaml`
- Build: Parallel builds with caching enabled
- Local testing: Warm containers (EAGER mode)

**CI Pipeline:**
- Not implemented yet
- Future: GitHub Actions → SAM deploy (planned in Phase 6)

## Environment Configuration

**Required env vars (set via Lambda Environment in CloudFormation):**
- `SYLLABUS_BUCKET` - S3 bucket name for syllabus storage
- `SYLLABUS_TABLE` - DynamoDB table name for parsed syllabi
- `AWS_REGION` - AWS region (defaults to `us-east-1` in client initialization)

**Secrets location:**
- AWS Secrets Manager - Not currently used (future for API keys, credentials)
- IAM roles - Primary authentication mechanism (no explicit secret storage)

**No .env files:**
- Environment variables are managed entirely through AWS CloudFormation and Lambda environment configuration
- No local .env file support needed for production

## Webhooks & Callbacks

**Incoming Webhooks:**
- None currently implemented

**Outgoing Webhooks:**
- None currently implemented

**Planned Event-Driven Architecture:**
- EventBridge trigger on S3 `PutObject` events in `documents/` prefix
- Purpose: Async processing of document tagging and summarization
- Target: Lambda function for background processing (planned in Phase 6)
- Bedrock Knowledge Bases will auto-sync S3 changes for embedding updates

## API Request/Response Patterns

**Base URL:**
- API Gateway endpoint: `https://{api-id}.execute-api.us-east-1.amazonaws.com/Prod`
- All routes prefixed with `/api/v1` via FastAPI router prefix

**Current Endpoints:**
- `GET /api/v1/health` - Health check
- `POST /api/v1/syllabus` - Upload and parse syllabus PDF
- `GET /api/v1/syllabus/{syllabus_id}` - Retrieve parsed syllabus

**File Upload Handling:**
- `Content-Type: multipart/form-data`
- Parsed by `python-multipart` in FastAPI
- Max file size: Not explicitly limited (planned: 10 MB default in Phase 6)

## External Service Error Handling

**Bedrock Integration (`backend/services/bedrock_service.py`):**
- `parse_syllabus_with_bedrock()` - Calls `bedrock.converse()` with document block
- No explicit retry logic (relies on boto3 defaults)
- JSON parsing errors propagated to caller
- Errors caught in router layer and returned as 500 with exception message

**DynamoDB Integration (`backend/services/dynamo_service.py`):**
- `store_syllabus()` - Uses `put_item()`
- `get_syllabus()` - Uses `get_item()`
- No error handling; failures propagated to service layer

**S3 Integration (`backend/services/syllabus_service.py`):**
- `put_object()` - Stores raw PDF file
- No explicit error handling; failures propagated

---

*Integration audit: 2026-03-13*
