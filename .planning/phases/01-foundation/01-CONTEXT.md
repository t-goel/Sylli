# Phase 1: Foundation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Stabilize the existing backend before any new features land. Three specific fixes: catch Bedrock JSON parse errors gracefully (FOUND-01), add timeout and retry handling to Bedrock invocations (FOUND-02), and rename all HelloWorld identifiers to Sylli (FOUND-03). No new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Error Response Format
- All Bedrock-related errors (parse failure, timeout, AWS service errors) return the same generic message: `{ "error": "Failed to parse syllabus. Please try again." }`
- No request ID or correlation token in the response body
- Log full error details server-side to CloudWatch (raw exception, response body, error type)
- The generic message is safe for the frontend to display directly

### Timeout Strategy
- Enforce timeout via boto3 Bedrock client config (~25s), leaving a 5s buffer before Lambda's 30s kill
- Do NOT increase Lambda timeout — keep at 30s
- A clean error is returned instead of a silent Lambda kill

### Retry Strategy
- 2 retries after initial failure (3 total attempts)
- Exponential backoff: 1s delay before retry 1, 2s before retry 2
- Retry ONLY on transient errors: `ReadTimeoutError`, `ThrottlingException`, `ServiceUnavailableException`
- Do NOT retry on JSON parse errors — the same bad Bedrock response will always fail again

### Test Cleanup
- Delete the broken legacy tests: `tests/unit/test_handler.py` and `tests/integration/test_api_gateway.py`
- Do NOT write new tests in Phase 1 — deferred to a later phase when the backend is more stable

### HelloWorld Purge
- Full purge: no HelloWorld identifiers should remain anywhere in the project
- Rename Lambda logical ID in `template.yaml` to `SylliFunction`
- Update `samconfig.toml` stack name to `sylli` (or `sylli-app`)
- Delete `hello_world/` directory entirely
- Delete broken legacy test files (already captured in Test Cleanup)
- Scan and update any remaining HelloWorld references (README, outputs, API names in template)

### Claude's Discretion
- Exact boto3 retry config implementation (botocore.config vs. manual retry loop)
- How to structure the logging calls (module-level logger vs. inline)
- Whether to add a `backend/utils/errors.py` or handle inline in bedrock_service.py

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/bedrock_service.py`: Target for FOUND-01 and FOUND-02 — json.loads() on line 56 needs try-catch; `bedrock.converse()` on line 30 needs timeout config
- `backend/routers/syllabus.py`: Broad `except Exception as e` on line 15 exposes internal errors — replace with the generic message

### Established Patterns
- Services raise exceptions naturally; routers catch and return HTTPException — keep this pattern, just improve the catch to return the agreed generic message
- Constants in UPPER_CASE at module top (`BUCKET_NAME`, `MODEL_ID`) — follow same pattern for timeout config constant

### Integration Points
- `template.yaml` `HelloWorldFunction` → `SylliFunction`: Also update Handler, Description, Outputs (HelloWorldApi), and ApplicationResourceGroup references
- `samconfig.toml` stack_name field
- `hello_world/app.py` file and directory to delete
- `tests/unit/test_handler.py` and `tests/integration/test_api_gateway.py` to delete

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for retry implementation (botocore.config with retry mode, or manual retry loop both acceptable).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-14*
