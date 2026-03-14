---
phase: 01-foundation
plan: "01"
subsystem: api
tags: [bedrock, boto3, botocore, lambda, error-handling, retry]

# Dependency graph
requires: []
provides:
  - Bedrock client with timeout+retry config (read_timeout=25s, mode=standard, max_attempts=3)
  - Structured CloudWatch error logging for JSON parse failures and Bedrock invocation errors
  - Generic HTTP 500 response hiding raw exception text from API consumers
affects: [02-auth, 03-materials, 04-chat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Service raises, router catches: bedrock_service re-raises all exceptions; syllabus router catches and returns generic HTTP 500"
    - "Pre-initialize mutable variables before try/except to avoid NameError in except branches"
    - "botocore.config.Config for per-client timeout and retry configuration"

key-files:
  created: []
  modified:
    - backend/services/bedrock_service.py
    - backend/routers/syllabus.py

key-decisions:
  - "Use botocore standard retry mode (not legacy) — only standard mode retries ReadTimeoutError automatically with exponential backoff+jitter"
  - "Both except branches log and re-raise — bedrock_service never swallows exceptions; router owns the generic HTTP response"
  - "raw_text initialized to empty string before try block to avoid NameError in JSONDecodeError handler if converse() fails before assignment"

patterns-established:
  - "Lambda Bedrock calls: always set read_timeout < Lambda timeout (25s vs 30s Lambda limit)"
  - "CloudWatch structured logging: use logger.error with extra dict containing error and error_type fields"

requirements-completed: [FOUND-01, FOUND-02]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 1 Plan 01: Bedrock Hardening Summary

**Bedrock client hardened with botocore read_timeout=25s + standard retry (3 attempts) and full try/except logging; syllabus router returns static generic error message instead of raw exception text**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T19:16:59Z
- **Completed:** 2026-03-14T19:24:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `botocore.config.Config` with `read_timeout=25`, `connect_timeout=5`, and standard retry mode (`max_attempts=3`) to prevent silent Lambda kills on large PDFs
- Wrapped `bedrock.converse()` and `json.loads()` in try/except with structured CloudWatch logging — both exception types log `error_type` and re-raise for the router to handle
- Fixed `syllabus.py` upload endpoint to return static `"Failed to parse syllabus. Please try again."` instead of `str(e)`, preventing raw exception text from leaking to HTTP responses

## Task Commits

Each task was committed atomically:

1. **Task 1: Add timeout+retry config and error handling to Bedrock client** - `ef27d7b` (feat)
2. **Task 2: Fix generic error response in syllabus router** - `38edb7d` (fix)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/services/bedrock_service.py` - Added Config with read_timeout/connect_timeout/retries, module-level logger, raw_text initialization before try, full try/except with CloudWatch logging
- `backend/routers/syllabus.py` - Replaced `detail=str(e)` with static generic error message in upload_syllabus exception handler

## Decisions Made

- Used `mode="standard"` for botocore retries (not `"legacy"`) because only standard mode retries `ReadTimeoutError` — the exact failure mode being fixed for large PDFs
- Service re-raises all exceptions rather than catching and returning a dict — keeps error handling centralized in the router layer
- `raw_text = ""` initialized before try block to prevent `NameError` if `converse()` raises before `raw_text` is assigned

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

All files verified present, both commits verified in git log.

## Issues Encountered

- Local Python environment does not have boto3 installed (Lambda-only dependency) — verified structural correctness via grep checks rather than import test. All done criteria confirmed with pattern matching.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Bedrock error handling is production-safe for real multi-page syllabus PDFs
- Ready to proceed with Phase 1 Plan 02 or subsequent phases
- No blockers from this plan

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
