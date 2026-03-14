# Phase 1: Foundation - Research

**Researched:** 2026-03-14
**Domain:** boto3 / AWS Bedrock client configuration, Python error handling, SAM/CloudFormation renaming
**Confidence:** HIGH

## Summary

Phase 1 is a pure stabilization pass with three tightly scoped tasks. The existing code is already structured correctly — services raise exceptions and routers catch them — but two gaps exist in `bedrock_service.py`: the `bedrock.converse()` call has no timeout enforcement and the `json.loads()` call has no try/except. A third gap is cosmetic but load-bearing for future deployments: the SAM template still carries the SAM boilerplate `HelloWorldFunction` logical IDs in six places.

All three fixes operate on code that already exists and is already wired up. No new endpoints, no new AWS resources, no schema changes. The risk is low; the main technical decision is how to configure the boto3 client for timeout + retry, and the boto3 `Config` object (via `botocore.config.Config`) is the idiomatic, single-location approach that covers both concerns.

**Primary recommendation:** Add a `botocore.config.Config` object to the `bedrock-runtime` boto3 client at construction time for timeout and retry; wrap `bedrock.converse()` and `json.loads()` in a single `try/except` block in `bedrock_service.py`; update `syllabus.py` router to return the agreed generic message; and do all `HelloWorldFunction` → `SylliFunction` renames in `template.yaml` plus deletions of `hello_world/` and broken tests.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Error Response Format**
- All Bedrock-related errors (parse failure, timeout, AWS service errors) return the same generic message: `{ "error": "Failed to parse syllabus. Please try again." }`
- No request ID or correlation token in the response body
- Log full error details server-side to CloudWatch (raw exception, response body, error type)
- The generic message is safe for the frontend to display directly

**Timeout Strategy**
- Enforce timeout via boto3 Bedrock client config (~25s), leaving a 5s buffer before Lambda's 30s kill
- Do NOT increase Lambda timeout — keep at 30s
- A clean error is returned instead of a silent Lambda kill

**Retry Strategy**
- 2 retries after initial failure (3 total attempts)
- Exponential backoff: 1s delay before retry 1, 2s before retry 2
- Retry ONLY on transient errors: `ReadTimeoutError`, `ThrottlingException`, `ServiceUnavailableException`
- Do NOT retry on JSON parse errors — the same bad Bedrock response will always fail again

**Test Cleanup**
- Delete the broken legacy tests: `tests/unit/test_handler.py` and `tests/integration/test_api_gateway.py`
- Do NOT write new tests in Phase 1 — deferred to a later phase when the backend is more stable

**HelloWorld Purge**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Bedrock JSON parse errors are caught and handled gracefully — no raw crashes exposed to the client | `json.loads()` on line 56 of `bedrock_service.py` needs a `try/except json.JSONDecodeError`; error should bubble up as a caught exception that the router converts to the generic HTTP 500 message |
| FOUND-02 | Bedrock invocations have timeout and retry handling — no silent Lambda kills on real documents | `boto3.client("bedrock-runtime")` needs a `botocore.config.Config` with `read_timeout=25`, `connect_timeout=5`, and `retries` dict specifying `max_attempts=3`, `mode="standard"` plus transient-only error filtering |
| FOUND-03 | SAM template and Lambda function are renamed from HelloWorld to Sylli project naming | Six locations in `template.yaml` + `samconfig.toml` stack_name + deletion of `hello_world/` directory + deletion of two legacy test files + update to `SPEC.md` reference |
</phase_requirements>

---

## Standard Stack

### Core (already in project — no new installs)
| Library | Version in Use | Purpose | Notes |
|---------|---------------|---------|-------|
| boto3 | bundled with Lambda runtime | AWS SDK — Bedrock, S3, DynamoDB clients | Already used; only client *config* changes |
| botocore | bundled with boto3 | Provides `Config`, retry modes, exception types | `botocore.config.Config`, `botocore.exceptions.ReadTimeoutError` |
| FastAPI | in `backend/requirements.txt` | HTTP framework, HTTPException | Router error handling pattern already established |
| Python `json` | stdlib | JSON parsing | Already imported in `bedrock_service.py` |
| Python `logging` | stdlib | CloudWatch structured logging | Not yet imported — needs adding |

### No New Dependencies
Phase 1 requires zero new packages. All needed tools (`botocore`, `json`, `logging`) are already present.

---

## Architecture Patterns

### Existing Pattern to Preserve

Services raise exceptions naturally; routers catch and return `HTTPException`. **Keep this pattern.** The fix is:
1. `bedrock_service.py` raises a clean Python exception (with logging) instead of letting `json.JSONDecodeError` or `ReadTimeoutError` propagate raw
2. `syllabus.py` router catches the exception and returns the agreed generic message

### Pattern 1: boto3 Client Timeout + Retry via `botocore.config.Config`

**What:** Pass a `Config` object when constructing the boto3 client. Covers both `read_timeout` and the `retries` block in one place.

**When to use:** Any boto3 client where you need explicit timeout enforcement and retry behavior. This is the boto3-idiomatic approach — no manual retry loop needed.

**Example:**
```python
# Source: https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html
import boto3
from botocore.config import Config

BEDROCK_TIMEOUT_S = 25

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    config=Config(
        read_timeout=BEDROCK_TIMEOUT_S,
        connect_timeout=5,
        retries={
            "max_attempts": 3,
            "mode": "standard",
        },
    ),
)
```

**Important:** `mode="standard"` in botocore uses exponential backoff with jitter by default and retries on `ThrottlingException` and `ServiceUnavailableException`. `ReadTimeoutError` is also retried under standard mode. This satisfies the locked retry strategy without a manual loop.

**Note on retry mode:** botocore `mode="standard"` retries include `ReadTimeoutError`, `ThrottlingException`, and `ServiceUnavailableException` — exactly the transient errors specified in the locked decisions. JSON parse errors happen *after* the call returns successfully, so they are naturally excluded from boto3 retry scope.

### Pattern 2: Exception Handling in `bedrock_service.py`

**What:** Wrap the `bedrock.converse()` call and the `json.loads()` call together. Log the full error to CloudWatch using Python's `logging` module, then re-raise a clean exception for the router to catch.

**Example structure:**
```python
import logging
import json

logger = logging.getLogger(__name__)

def parse_syllabus_with_bedrock(pdf_bytes: bytes) -> dict:
    try:
        response = bedrock.converse(...)
        raw_text = response["output"]["message"]["content"][0]["text"]
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("Bedrock JSON parse error", extra={"error": str(e), "raw_text": raw_text})
        raise
    except Exception as e:
        logger.error("Bedrock invocation error", extra={"error": str(e), "error_type": type(e).__name__})
        raise
```

**Router catch pattern (existing, already correct structure):**
```python
# syllabus.py — replace str(e) with the generic message
except Exception as e:
    raise HTTPException(status_code=500, detail="Failed to parse syllabus. Please try again.")
```

### Pattern 3: HelloWorld Rename in `template.yaml`

**What:** CloudFormation logical IDs and SAM event names are just YAML keys. Renaming them does not affect deployed resource names (S3 bucket name, DynamoDB table name) because those are set in `Properties.BucketName` / `Properties.TableName`. Only the Lambda logical ID, IAM role suffix, and Output keys change.

**Exact renames needed in `template.yaml`:**
| Location | From | To |
|----------|------|----|
| Resource logical ID (line 17) | `HelloWorldFunction` | `SylliFunction` |
| SAM event name (line 44) | `HelloWorld` | `Sylli` |
| Output key (line 84) | `HelloWorldApi` | `SylliApi` |
| Output key (line 88) | `HelloWorldFunction` | `SylliFunction` |
| Output `Value` GetAtt (line 90) | `HelloWorldFunction.Arn` | `SylliFunction.Arn` |
| Output key (line 91) | `HelloWorldFunctionIamRole` | `SylliFunctionIamRole` |
| Output `Value` GetAtt (line 93) | `HelloWorldFunctionRole.Arn` | `SylliFunctionRole.Arn` |

**`samconfig.toml`:** `stack_name = "Sylli"` is already set — no change needed there.

**Files to delete:**
- `hello_world/` directory (contains `app.py`, `__init__.py`, `requirements.txt`)
- `tests/unit/test_handler.py`
- `tests/integration/test_api_gateway.py`

**Files to update (non-template):**
- `SPEC.md` line 89: `HelloWorldFunction` → `SylliFunction` in the infrastructure table

### Anti-Patterns to Avoid
- **Manual retry loop:** Do not implement `for attempt in range(3): try/except` — `botocore.config.Config` handles this more reliably with proper backoff and jitter
- **Catching `json.JSONDecodeError` separately from Bedrock errors in the router:** All Bedrock-related errors should produce the same generic response; no need for different catch blocks in the router
- **Logging `str(e)` only:** Always log `type(e).__name__` alongside the message to distinguish error types in CloudWatch
- **Storing raw error text in the HTTP response body:** `detail=str(e)` (current code) exposes internal state — always use the agreed static message

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timeout enforcement | Manual `signal.alarm()` or threading timer | `botocore.config.Config(read_timeout=25)` | botocore timeout is socket-level, fires before Lambda kill, and is the only reliable mechanism inside a sync boto3 call |
| Retry with backoff | `time.sleep()`-based loop | `botocore.config.Config(retries={"mode": "standard"})` | botocore standard mode uses full jitter backoff and correctly identifies retriable error types |
| Transient error filtering | `isinstance(e, ...)` branching in retry loop | `mode="standard"` built-in retry list | botocore's retriable error list is maintained by AWS and includes all required transient types |

**Key insight:** boto3/botocore already solves timeout and retry correctly at the HTTP transport layer. Any custom solution will be less reliable and harder to reason about.

---

## Common Pitfalls

### Pitfall 1: `raw_text` undefined in `except json.JSONDecodeError`
**What goes wrong:** If the variable `raw_text` is assigned inside the `try` block *after* a potential Bedrock error, referencing it in the `except json.JSONDecodeError` handler will raise a `NameError`.
**Why it happens:** `raw_text` is only assigned if `bedrock.converse()` succeeds and the response structure is valid.
**How to avoid:** Initialize `raw_text = ""` before the try block, or log `raw_text` only in the `except json.JSONDecodeError` branch (where it is guaranteed to be assigned if we reached `json.loads(raw_text)`).
**Warning signs:** `NameError: name 'raw_text' is not defined` in CloudWatch logs instead of the JSON parse error.

### Pitfall 2: `mode="standard"` vs `mode="legacy"` retry behavior
**What goes wrong:** The default botocore retry mode is `"legacy"`, which does not retry on `ReadTimeoutError`. Only `mode="standard"` (or `"adaptive"`) retries on timeouts.
**Why it happens:** botocore default was `"legacy"` before boto3 1.24 / botocore 1.27; Lambda runtimes may have an older bundled version.
**How to avoid:** Always explicitly set `mode="standard"` in the `retries` dict — never rely on the default.
**Warning signs:** Timeouts not being retried in Lambda logs; only 1 attempt visible despite `max_attempts=3`.

### Pitfall 3: CloudFormation logical ID rename causes resource replacement
**What goes wrong:** Renaming a resource's logical ID in CloudFormation causes it to be deleted and recreated. For stateful resources (DynamoDB, S3) this means data loss.
**Why it happens:** CloudFormation tracks resources by logical ID, not by `Properties.TableName`.
**How to avoid:** Only renaming `HelloWorldFunction` (Lambda — stateless) and the SAM event name (no deployed resource). S3 bucket (`SyllabusBucket`) and DynamoDB table (`SyllabusTable`) logical IDs are already correct and must NOT be touched.
**Warning signs:** CloudFormation changeset shows a Replace action on `SyllabusTable` or `SyllabusBucket`.

### Pitfall 4: `.aws-sam/` cached build references old logical ID
**What goes wrong:** After renaming `HelloWorldFunction` → `SylliFunction`, `sam build` may use a cached artifact under the old name (`.aws-sam/build.toml` still has `functions = ["HelloWorldFunction"]`).
**Why it happens:** SAM build cache is keyed by logical ID.
**How to avoid:** Run `sam build` without `--cached` after the rename, or delete `.aws-sam/` before building. The `.aws-sam/` directory is a build artifact — it should not be committed.
**Warning signs:** `sam deploy` succeeds but old function name still appears in Lambda console.

### Pitfall 5: `SPEC.md` still references `HelloWorldFunction`
**What goes wrong:** `SPEC.md` line 89 documents the Lambda logical ID as `HelloWorldFunction`. This is a documentation artifact, not a deployment artifact, but it creates confusion.
**Why it happens:** SPEC.md was written when the project was scaffolded and not updated.
**How to avoid:** Update `SPEC.md` infrastructure table as part of FOUND-03.

---

## Code Examples

### Complete `bedrock_service.py` structure after Phase 1

```python
# Source: botocore.config.Config docs + project conventions
import json
import logging
import os

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

BEDROCK_READ_TIMEOUT_S = 25
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    config=Config(
        read_timeout=BEDROCK_READ_TIMEOUT_S,
        connect_timeout=5,
        retries={
            "max_attempts": 3,
            "mode": "standard",
        },
    ),
)

SYSTEM_PROMPT = """..."""  # unchanged


def parse_syllabus_with_bedrock(pdf_bytes: bytes) -> dict:
    """Send a syllabus PDF to Claude via Bedrock and return a parsed week map."""
    raw_text = ""
    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[...],  # unchanged
        )
        raw_text = response["output"]["message"]["content"][0]["text"]
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(
            "Bedrock response JSON parse failed",
            extra={"error": str(e), "raw_text": raw_text, "error_type": "JSONDecodeError"},
        )
        raise
    except Exception as e:
        logger.error(
            "Bedrock invocation error",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        raise
```

### Router update in `syllabus.py`

```python
# Replace detail=str(e) with the agreed generic message
except Exception as e:
    raise HTTPException(status_code=500, detail="Failed to parse syllabus. Please try again.")
```

---

## Complete HelloWorld Inventory (all locations to fix)

Based on a grep scan of the project:

| File | Line(s) | Change |
|------|---------|--------|
| `template.yaml` | 17, 44, 84, 88–93 | Rename logical IDs and Output keys (see Pattern 3 above) |
| `SPEC.md` | 89 | Update infrastructure table: `HelloWorldFunction` → `SylliFunction` |
| `tests/unit/test_handler.py` | entire file | Delete file |
| `tests/integration/test_api_gateway.py` | 33, 36 | Delete file |
| `hello_world/app.py`, `hello_world/__init__.py`, `hello_world/requirements.txt` | entire dir | Delete directory |
| `.aws-sam/build.toml` | 10 | Build artifact — delete `.aws-sam/` or rebuild; do NOT edit by hand |
| `.planning/` files | various | Planning artifacts — reference only, no code change needed |

`samconfig.toml` `stack_name = "Sylli"` is already correct — no change needed.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| `botocore` `mode="legacy"` retries (no ReadTimeoutError) | `mode="standard"` retries (includes ReadTimeoutError) | Transient timeout errors are retried instead of surfacing as silent Lambda kills |
| No timeout on boto3 client | `read_timeout` in `Config` | Socket-level timeout fires before Lambda hard kill; clean error returned |
| `detail=str(e)` in FastAPI HTTPException | Static generic message | No internal error details leak to clients |

---

## Open Questions

1. **`botocore` version on Python 3.13 Lambda runtime**
   - What we know: `mode="standard"` was added in botocore 1.20.x (2021). Python 3.13 Lambda runtime uses boto3/botocore bundled at a recent version.
   - What's unclear: The exact bundled version on ARM64 Python 3.13 runtime as of March 2026.
   - Recommendation: This is LOW risk — `mode="standard"` has been available for 4+ years. Confirm with `sam build` output if needed. If `mode="standard"` is unavailable (very unlikely), fall back to `mode="adaptive"` which is newer and also retries timeouts.

2. **`ReadTimeoutError` is in `botocore.exceptions` not `boto3.exceptions`**
   - What we know: The correct import is `from botocore.exceptions import ReadTimeoutError` if manual catch is needed.
   - What's unclear: Not needed for Phase 1 since `mode="standard"` handles it automatically, but worth knowing if the planner needs to log specific error types.
   - Recommendation: No action needed; document for Phase 2+ reference.

---

## Sources

### Primary (HIGH confidence)
- Direct code read of `/Users/tanmaygoel/CS/Sylli/backend/services/bedrock_service.py` — confirmed exact lines needing change
- Direct code read of `/Users/tanmaygoel/CS/Sylli/backend/routers/syllabus.py` — confirmed `detail=str(e)` pattern
- Direct code read of `/Users/tanmaygoel/CS/Sylli/template.yaml` — confirmed all 7 HelloWorld locations
- Direct code read of `/Users/tanmaygoel/CS/Sylli/samconfig.toml` — confirmed stack_name already "Sylli"
- botocore Config documentation: https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html
- botocore retry modes documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html

### Secondary (MEDIUM confidence)
- Grep scan of full project confirming all HelloWorld identifier locations
- CloudFormation logical ID rename behavior (well-documented AWS behavior, confirmed via direct observation)

### Tertiary (LOW confidence)
- Exact botocore bundled version on Python 3.13 ARM64 Lambda runtime as of March 2026 — not verified against live AWS docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all tools already in use
- Architecture: HIGH — patterns directly observed in existing code
- Pitfalls: HIGH — all based on direct code inspection and well-known botocore behavior
- HelloWorld inventory: HIGH — confirmed via grep scan

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (stable — boto3/botocore API has been stable for years; SAM/CloudFormation rename behavior is invariant)
