---
phase: 04-ai-tutor
plan: "04"
subsystem: api
tags: [python, lambda, error-handling, logging, dynamodb, cloudwatch]

# Dependency graph
requires:
  - phase: 03-materials-and-library
    provides: material embedding pipeline with embed_status field in DynamoDB

provides:
  - confirm_material_week with proper Lambda invocation error propagation
  - embed_status='error' DynamoDB update on Lambda failure
  - logger.exception logging for CloudWatch visibility
  - Frontend poll termination on invocation failure (returns embed_status='error')

affects: [04-ai-tutor, rag-pipeline, material-embedding]

# Tech tracking
tech-stack:
  added: []
  patterns: [exception logging via logger.exception before early return, error status propagation to caller]

key-files:
  created: []
  modified: [backend/services/material_service.py]

key-decisions:
  - "On Lambda invoke failure, return embed_status='error' immediately (early return) rather than falling through to invoked=False path — DynamoDB and API response both reflect error state"

patterns-established:
  - "Error propagation pattern: log exception -> update DynamoDB status -> return error state immediately, do not continue happy path"

requirements-completed: [TUTOR-01]

# Metrics
duration: 1min
completed: 2026-03-16
---

# Phase 4 Plan 04: Lambda Error Propagation Summary

**Silent Lambda invocation failures now set embed_status='error' in DynamoDB, log to CloudWatch via logger.exception, and return embed_status='error' immediately so the frontend poll terminates with a visible failure badge**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-16T21:09:00Z
- **Completed:** 2026-03-16T21:09:49Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `import logging` and module-level `logger = logging.getLogger(__name__)` to material_service.py
- Replaced silent `except Exception: pass` in `confirm_material_week` with proper error propagation
- Lambda invocation failures now call `update_material_embed_status(material_id, "error")` before returning
- Function returns `{"embed_status": "error"}` immediately on failure, terminating frontend polling
- delete_material's intentional `except Exception: pass` (for missing S3 objects) left unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace silent except with error propagation in confirm_material_week** - `44c7b85` (fix)

**Plan metadata:** `0f8a615` (docs: complete plan)

## Files Created/Modified
- `backend/services/material_service.py` - Added logging import and logger, replaced bare except:pass with exception logging + error status update + early return

## Decisions Made
- On Lambda invoke failure, use an early return inside the except block rather than setting a flag and checking it afterward — this ensures DynamoDB state and API response are always in sync, and the happy path (invoked=True → "processing", no EMBED_FUNCTION_NAME → "pending") is completely unchanged.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 gap closure complete: embedding errors are now visible to operators (CloudWatch) and users (frontend "Embedding failed" badge)
- Frontend already handles embed_status='error' (MaterialUpload.tsx lines 262-264) — no frontend changes needed
- Phase 5 can proceed without concern about silent embedding failures masking RAG quality issues

---
*Phase: 04-ai-tutor*
*Completed: 2026-03-16*
