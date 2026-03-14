# Codebase Concerns

**Analysis Date:** 2026-03-13

## Tech Debt

**Generic Exception Handling:**
- Issue: Broad `except Exception as e` catches all errors without differentiation, including unintended failures
- Files: `backend/routers/syllabus.py` (line 15)
- Impact: Difficult to debug; masks unexpected errors; exposes sensitive error details to API consumers
- Fix approach: Replace with specific exception types (e.g., `S3ClientError`, `DynamoDBError`, `json.JSONDecodeError`). Log unexpected errors server-side, return generic messages to client.

**No Structured Logging:**
- Issue: No logging framework in use; no server-side observability for errors, performance, or request tracing
- Files: `backend/services/bedrock_service.py`, `backend/services/syllabus_service.py`, `backend/services/dynamo_service.py`
- Impact: Cannot diagnose production failures; cannot track performance bottlenecks; no audit trail for security events
- Fix approach: Add `logging` module with structured JSON logs. Log at INFO level for key operations (file upload, Bedrock calls), ERROR level for failures.

**Hardcoded Environment Variable Defaults:**
- Issue: Default values hardcoded as fallback when env vars not set (e.g., `SYLLABUS_BUCKET` defaults to `sylli-syllabus-bucket`)
- Files: `backend/services/syllabus_service.py` (line 12), `backend/services/dynamo_service.py` (line 5)
- Impact: Configuration not enforced; silent failures if resources don't exist; different behavior in dev vs. production
- Fix approach: Validate all required env vars on Lambda startup. Fail fast if missing. Use environment-specific `.env` files for development.

**No Input Validation on JSON Parsing:**
- Issue: `json.loads(raw_text)` in Bedrock response parsing has no try-catch; malformed response crashes the function
- Files: `backend/services/bedrock_service.py` (line 56)
- Impact: If Claude returns invalid JSON, the upload fails without recovery; user sees generic 500 error
- Fix approach: Wrap in try-catch, log the raw response, return structured error with retry guidance.

**Bare boto3 Clients:**
- Issue: boto3 clients initialized at module load time without retry configuration or error handling
- Files: `backend/services/syllabus_service.py` (line 11), `backend/services/dynamo_service.py` (line 4), `backend/services/bedrock_service.py` (line 5)
- Impact: Transient AWS failures (rate limits, brief outages) crash the Lambda; no automatic retry; poor resilience
- Fix approach: Use boto3 session with explicit config (retries: 3, backoff: exponential). Consider using `botocore.exceptions.ClientError` catch blocks.

## Known Bugs

**Missing Upload Result Validation:**
- Symptoms: `fetch_syllabus()` returns `None` if document not found in DynamoDB, but caller (`syllabus.py` line 22) doesn't handle all edge cases
- Files: `backend/routers/syllabus.py` (line 22-24), `backend/services/dynamo_service.py` (line 26)
- Trigger: Retrieve a syllabus_id that was never uploaded; rapid concurrent uploads with duplicate IDs
- Workaround: Always use UUID4 for IDs (currently done), but concurrency during same-millisecond uploads could collide

**No Async/Await Consistency:**
- Symptoms: Functions marked `async` but call blocking boto3 operations (not truly async)
- Files: `backend/services/syllabus_service.py` (lines 15-43), `backend/routers/syllabus.py` (lines 8, 20)
- Trigger: Under high concurrent load, Lambda may block unnecessarily on I/O, reducing throughput
- Workaround: Current code works but doesn't leverage async benefits. Migration to `aioboto3` would improve concurrency.

**Bedrock Model ID Hardcoded:**
- Symptoms: Model `anthropic.claude-3-5-sonnet-20241022-v2:0` hardcoded; if deprecated, deployment breaks
- Files: `backend/services/bedrock_service.py` (line 7)
- Trigger: AWS deprecates model version; team switches to newer Claude without code change
- Workaround: Always update `MODEL_ID` before model version reaches end-of-life; no automated alerting

**PDF File Validation Only by Extension:**
- Symptoms: Only checks `.pdf` filename extension, not actual file type
- Files: `backend/routers/syllabus.py` (line 10)
- Trigger: User uploads file named `file.pdf` that is actually a text file or binary garbage; Bedrock fails to process
- Workaround: Add magic byte validation or use `python-magic` to verify MIME type; return user-friendly error.

## Security Considerations

**IAM Overly Permissive:**
- Risk: `bedrock:InvokeModel` permission granted on `*` (all models); no resource restrictions
- Files: `template.yaml` (lines 38-42)
- Current mitigation: Hardcoded MODEL_ID in code; organization trusts developers
- Recommendations:
  1. Restrict IAM to specific model ARN: `arn:aws:bedrock:region:account:foundation-model/anthropic.claude-*`
  2. Add cost controls via AWS Service Control Policies (SCPs)
  3. Audit Bedrock API usage in CloudWatch

**S3 Bucket Configuration Missing Security Defaults:**
- Risk: No server-side encryption, versioning, or public access block configured
- Files: `template.yaml` (lines 62-65)
- Current mitigation: S3 bucket defaults to private; no explicit public access
- Recommendations:
  1. Enable S3 server-side encryption (SSE-S3 or SSE-KMS)
  2. Enable versioning to protect against accidental deletion
  3. Add bucket policy to deny unencrypted uploads
  4. Add `PublicAccessBlockConfiguration` with all flags set to true

**Bedrock Response Exposed to Client:**
- Risk: Raw Bedrock parsing errors (including internal traces) returned via `str(e)` in HTTPException
- Files: `backend/routers/syllabus.py` (line 16)
- Current mitigation: None
- Recommendations:
  1. Log full error server-side (with request ID for correlation)
  2. Return generic error message to client: `{"error": "Failed to parse syllabus. Please try again."}`
  3. Implement request ID tracking for customer support

**No Authentication on Endpoints:**
- Risk: All endpoints (`POST /syllabus`, `GET /syllabus/{id}`) are publicly accessible
- Files: `backend/routers/syllabus.py`
- Current mitigation: None
- Recommendations:
  1. Implement API key validation via middleware (e.g., FastAPI `Depends()`)
  2. Integrate AWS Cognito for user authentication
  3. Add request signing with AWS Signature Version 4 for machine-to-machine calls

**Secrets Management:**
- Risk: AWS credentials loaded implicitly by boto3 from Lambda execution role; no rotation mechanism visible
- Files: All files using boto3
- Current mitigation: Uses IAM execution role (best practice for Lambda)
- Recommendations:
  1. Document that credentials are managed by Lambda execution role
  2. Implement credential rotation policy (AWS Secrets Manager for external integrations)
  3. Add CloudTrail logging for all boto3 API calls

**PDF Content Passed as Raw Bytes to Bedrock:**
- Risk: Large PDFs (megabytes) sent to Bedrock without size validation; potential DDoS vector
- Files: `backend/services/bedrock_service.py` (line 41), `backend/routers/syllabus.py` (line 17)
- Current mitigation: None
- Recommendations:
  1. Add file size limit check (e.g., max 50 MB) in upload endpoint
  2. Return 413 Payload Too Large if exceeded
  3. Document size limits for users

## Performance Bottlenecks

**Synchronous Bedrock API Call Blocks Lambda:**
- Problem: `bedrock.converse()` call in `parse_syllabus_with_bedrock()` is blocking; no timeout set
- Files: `backend/services/bedrock_service.py` (lines 30-53)
- Cause: Waiting for Bedrock to parse PDF; can take 30+ seconds for large documents; Lambda timeout is 30s (template.yaml line 11)
- Improvement path:
  1. Implement asynchronous processing: upload → trigger Lambda → Lambda parses and stores result
  2. Use S3 event notifications (EventBridge) to trigger parsing asynchronously
  3. Return `202 Accepted` with tracking ID instead of waiting for result
  4. Client polls or uses webhook to retrieve result when ready

**No Pagination on DynamoDB Queries:**
- Problem: `get_syllabus()` returns single item; if future features query multiple syllabi, no limit on results
- Files: `backend/services/dynamo_service.py` (line 22-26)
- Cause: N/A for current endpoints, but architectural gap
- Improvement path: Add `limit` and `exclusive_start_key` parameters; implement cursor-based pagination for future list endpoints

**S3 Upload Synchronous with No Progress Tracking:**
- Problem: Large PDF uploads block the request; no way to show upload progress to user
- Files: `backend/services/syllabus_service.py` (line 23)
- Cause: Entire file read into memory (`await file.read()` line 17), then uploaded to S3 as single object
- Improvement path:
  1. Use multipart upload for files >10 MB
  2. Implement streaming upload with progress tracking
  3. Return upload job ID; client monitors progress via separate endpoint

## Fragile Areas

**Bedrock JSON Response Parsing:**
- Files: `backend/services/bedrock_service.py` (lines 28-56)
- Why fragile:
  1. Claude instructed to return "ONLY valid JSON" but model can hallucinate markdown blocks or explanatory text
  2. System prompt assumes Claude will follow instructions; no fallback if it doesn't
  3. Missing schema validation; no guarantee response matches expected `{"course_name": ..., "weeks": [...]}` structure
- Safe modification:
  1. Parse JSON with error recovery: if first parse fails, try extracting JSON from markdown blocks (```json...```)
  2. Validate schema using `pydantic.BaseModel` with strict mode
  3. Return partial result with warnings if required fields missing
- Test coverage: No tests exist for malformed responses

**DynamoDB Item Storage Without Schema Validation:**
- Files: `backend/services/dynamo_service.py` (lines 8-19)
- Why fragile:
  1. No validation that `week_map` parameter conforms to expected schema
  2. DynamoDB stores arbitrary Python dicts; no type constraints
  3. If upstream parsing changes structure, database operations fail silently
- Safe modification:
  1. Create `SyllabusRecord` Pydantic model with schema
  2. Validate before storing: `SyllabusRecord(**syllabus_data).dict()`
  3. Add DynamoDB Global Secondary Index on `uploaded_at` for time-based queries
- Test coverage: No tests for DynamoDB operations

**Lambda Timeout Risk:**
- Files: `template.yaml` (line 11), `backend/services/bedrock_service.py` (line 30)
- Why fragile:
  1. Lambda timeout set to 30 seconds (template.yaml)
  2. Bedrock `converse()` call has no timeout; can exceed 30s on complex PDFs
  3. If timeout hit, request fails with no partial result saved
- Safe modification:
  1. Set explicit timeout on Bedrock client: `config = botocore.config.Config(connect_timeout=25, read_timeout=25)` (leaving 5s buffer)
  2. Implement graceful degradation: catch timeout, return partial result if available
  3. Increase Lambda timeout to 60s for PDF processing phase
- Test coverage: No timeout tests

## Scaling Limits

**S3 Bucket Request Rate:**
- Current capacity: Default S3 rate limit is 3,500 PUT requests/second per partition
- Limit: If >1 user uploads simultaneously, S3 requests may throttle (unlikely near-term)
- Scaling path: S3 automatically scales; if needed, use multiple prefixes (e.g., `syllabus/{uuid_prefix_0}/{uuid}`) to distribute load

**DynamoDB Scaling:**
- Current capacity: Table uses `PAY_PER_REQUEST` billing (unlimited throughput)
- Limit: DynamoDB Streams (if added later) limited to 100 records/second baseline
- Scaling path: Current setup scales well; if query patterns become complex, migrate to provisioned capacity with auto-scaling

**Bedrock API Rate Limits:**
- Current capacity: Depends on AWS account tier; default ~100 requests/minute for new accounts
- Limit: If multiple concurrent uploads trigger Bedrock calls, rate limiting kicks in (user sees 429 errors)
- Scaling path: Request AWS Service Quotas increase for Bedrock `InvokeModel`; implement exponential backoff retry logic

**Lambda Memory & Concurrent Execution:**
- Current capacity: Default 128 MB memory per Lambda; concurrent execution quota ~1,000 per region
- Limit: Large PDFs (>50 MB) risk memory errors; high concurrency exhausts quota
- Scaling path:
  1. Increase Lambda memory to 512 MB (increases cost but improves performance)
  2. Implement queue-based architecture: uploads → SQS → Lambda workers (vs. direct invocation)
  3. Request concurrent execution quota increase from AWS

## Dependencies at Risk

**boto3 Version Pinning:**
- Risk: `requirements.txt` does not pin boto3 version; major version bumps could introduce breaking changes
- Files: `backend/requirements.txt` (lists only `boto3` with no version)
- Impact: CI/CD may deploy with incompatible boto3 version; API behavior changes unexpectedly
- Migration plan:
  1. Pin exact versions: `boto3==1.36.0` (or latest compatible)
  2. Add `botocore` pinning (transitive dependency)
  3. Test version upgrades in staging before production deployment

**mangum Version Not Pinned:**
- Risk: Mangum (ASGI-to-Lambda adapter) version not constrained; breaking changes to FastAPI integration possible
- Files: `backend/requirements.txt`
- Impact: Lambda handler may fail if Mangum major version changes
- Migration plan: Pin to stable version (e.g., `mangum==0.28.0`); update after testing

**FastAPI Version Not Pinned:**
- Risk: FastAPI fast release cycle; security patches and breaking changes frequent
- Files: `backend/requirements.txt`
- Impact: Stale FastAPI can accumulate security vulnerabilities
- Migration plan: Pin FastAPI to security-patched version with constraints (e.g., `fastapi>=0.109.0,<1.0`)

**python-multipart Presence Not Documented:**
- Risk: Dependency listed in requirements but usage not clear
- Files: `backend/requirements.txt`
- Impact: Unclear why this is needed; may be unnecessary
- Migration plan: Verify if needed for UploadFile handling; if not used, remove to reduce attack surface

## Missing Critical Features

**No Authentication or Authorization:**
- Problem: Anyone with API endpoint URL can upload syllabi and retrieve them
- Blocks: Production deployment; sensitive course materials unprotected
- Recommendations:
  1. Implement API key authentication (quick fix for MVP)
  2. Integrate AWS Cognito for user identity
  3. Add authorization: users can only access their own syllabi

**No Audit Logging:**
- Problem: Cannot track who uploaded what, when, or why
- Blocks: FERPA/GDPR compliance (if handling student data)
- Recommendations:
  1. Log all upload/retrieval operations with user ID, timestamp, file name
  2. Store logs in CloudWatch (automatically integrated with Lambda)
  3. Implement log retention policy (e.g., 30 days for operational logs)

**No Error Recovery or Retry Logic:**
- Problem: If S3 upload fails, Bedrock parsing still proceeds (may fail downstream)
- Blocks: Reliable operation; users cannot retry failed uploads
- Recommendations:
  1. Implement transaction-like pattern: verify S3 upload succeeded before calling Bedrock
  2. Add user-facing retry endpoint: `POST /syllabus/{syllabus_id}/retry`
  3. Store job state (pending, processing, succeeded, failed) in DynamoDB

**No File Size or Type Validation:**
- Problem: Only extension checked; no validation of actual file contents
- Blocks: Handling corrupted or malicious files gracefully
- Recommendations:
  1. Add magic byte validation using `python-magic-bin`
  2. Validate PDF structure (e.g., starts with `%PDF`)
  3. Implement malware scanning (AWS GuardDuty or third-party)

## Test Coverage Gaps

**No Unit Tests for Service Layer:**
- What's not tested: `bedrock_service.parse_syllabus_with_bedrock()`, `dynamo_service.store_syllabus()`, `dynamo_service.get_syllabus()`
- Files: `backend/services/bedrock_service.py`, `backend/services/dynamo_service.py`, `backend/services/syllabus_service.py`
- Risk: Schema changes, boto3 errors, or Bedrock API changes break silently until production
- Priority: **High** — Services contain core logic

**No Integration Tests for API Endpoints:**
- What's not tested: Full flow of uploading syllabus → parsing with Bedrock → storing in DynamoDB → retrieving
- Files: `backend/routers/syllabus.py`
- Risk: End-to-end flow may work locally but fail in Lambda environment or with real AWS services
- Priority: **High** — End-to-end behavior critical

**No Tests for Error Handling:**
- What's not tested: Malformed PDFs, S3 upload failures, Bedrock timeouts, DynamoDB errors
- Files: `backend/routers/syllabus.py` (exception handlers)
- Risk: Error paths never executed; silent failures in production
- Priority: **Medium** — Error paths rare but critical

**No Tests for JSON Parsing Edge Cases:**
- What's not tested: Bedrock returning invalid JSON, missing fields in response, markdown-wrapped JSON
- Files: `backend/services/bedrock_service.py` (line 56)
- Risk: Fragile parsing leads to production crashes
- Priority: **High** — Core failure point

**Legacy Test Files Not Updated:**
- What's not tested: Tests in `tests/unit/test_handler.py` and `tests/integration/test_api_gateway.py` reference `hello_world` module, not actual Sylli endpoints
- Files: `tests/unit/test_handler.py`, `tests/integration/test_api_gateway.py`
- Risk: Test suite is broken and provides false confidence
- Priority: **Critical** — Tests must reflect current code

---

*Concerns audit: 2026-03-13*
