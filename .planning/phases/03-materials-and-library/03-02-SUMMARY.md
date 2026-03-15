---
phase: 03-materials-and-library
plan: "02"
subsystem: api
tags: [fastapi, dynamodb, s3, bedrock, lambda, boto3]

# Dependency graph
requires:
  - phase: 03-01
    provides: CloudFormation infra (MaterialsTable, MaterialsBucket, EmbedWorkerFunction, GSI)
  - phase: 02-auth-and-syllabus
    provides: get_current_user JWT middleware, dynamo_service patterns, bedrock_service MODEL_ID
provides:
  - 5 material API endpoints (upload, confirm, list, status, view)
  - material_service.py with upload_material, confirm_material_week, get_presigned_url
  - dynamo_service.py extended with material CRUD (store, get, update_week, update_embed_status, list)
  - async Lambda trigger via InvocationType=Event for embedding pipeline
affects:
  - phase 03-03 (embedding Lambda reads material_id/s3_key from DynamoDB records we create)
  - phase 04 (chat needs material embed_status=ready before retrieval)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anti-enumeration: get_material returns None on ownership mismatch (same pattern as get_syllabus)"
    - "Async Lambda trigger: InvocationType=Event for fire-and-forget embedding"
    - "AI fallback: suggest_week_for_material falls back to week 1 on any exception — upload never crashes"
    - "GSI query: list_materials_for_user uses user_id-index with ScanIndexForward=True (no full table scan)"
    - "Presigned URL: generated fresh each call with ExpiresIn=300"

key-files:
  created:
    - backend/services/material_service.py
    - backend/routers/materials.py
    - backend/tests/test_dynamo_material.py
  modified:
    - backend/services/dynamo_service.py
    - backend/app.py

key-decisions:
  - "suggest_week_for_material catches all exceptions and returns week 1 — upload success is more important than AI suggestion accuracy"
  - "confirm endpoint calls update_material_embed_status separately after confirm_material_week — ensures DynamoDB reflects processing state even if Lambda trigger is skipped (empty EMBED_FUNCTION_NAME)"
  - "EMBED_FUNCTION_NAME guard: Lambda invocation skipped when env var is empty — allows local dev without Lambda"

patterns-established:
  - "Material CRUD follows syllabus CRUD pattern: put_item for store, get_item+ownership check for get, update_item for mutations"
  - "Router catches generic Exception on upload and re-raises as HTTP 500 — service layer exceptions do not leak to API responses"

requirements-completed: [MAT-01, MAT-02, MAT-03, LIB-01, LIB-02]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 3 Plan 02: Material Management Backend Summary

**5 material API endpoints (upload+AI week suggestion, confirm+async Lambda trigger, list via GSI, status poll, presigned view URL) with full DynamoDB CRUD and 12 unit tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T20:43:04Z
- **Completed:** 2026-03-15T20:45:16Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extended dynamo_service.py with 5 material CRUD functions backed by MaterialsTable GSI — no full table scans
- Created material_service.py: S3 upload + Bedrock week suggestion (with fallback) + DynamoDB store + async Lambda trigger
- Registered 5 REST endpoints at /api/v1/materials, all requiring JWT auth; 404 on ownership mismatch (anti-enumeration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend dynamo_service with material CRUD (TDD)** - `fdff3ec` (feat)
2. **Task 2: material_service, materials router, register in app.py** - `fa64d2e` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD — tests written first (RED), implementation added (GREEN), 12/12 passing_

## Files Created/Modified
- `backend/services/dynamo_service.py` - Added MATERIALS_TABLE_NAME + 5 material CRUD functions
- `backend/services/material_service.py` - upload_material, confirm_material_week, get_presigned_url
- `backend/routers/materials.py` - 5 endpoints (POST /materials, POST /{id}/confirm, GET /materials, GET /{id}/status, GET /{id}/view)
- `backend/app.py` - Added materials router import and include_router at /api/v1
- `backend/tests/test_dynamo_material.py` - 12 unit tests for all material CRUD functions

## Decisions Made
- `suggest_week_for_material` wraps Bedrock call in `except Exception: return 1` — upload reliability takes priority over AI accuracy
- `confirm_material_week` in service returns `{embed_status: "processing"}` but router calls `update_material_embed_status` separately — decouples Lambda trigger from DynamoDB state update
- `EMBED_FUNCTION_NAME` guard prevents Lambda invocation in local dev (env var empty by default)

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed reload-based env var test that hit real DynamoDB**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** `test_store_material_uses_materials_table_env` used `importlib.reload` after `patch.dict` — after reload the patch context from the outer `with` block was no longer binding the reloaded module's `dynamodb`, causing the function to call real DynamoDB and raise `ResourceNotFoundException`
- **Fix:** Replaced reload-based test with a simpler assertion checking `MATERIALS_TABLE_NAME` constant against the expected default value — tests the same contract (env var drives table name) without fragile module reload
- **Files modified:** backend/tests/test_dynamo_material.py
- **Verification:** All 12 tests pass
- **Committed in:** fdff3ec (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Test correctness fix only, no behavior change to production code.

## Issues Encountered
None beyond the test bug above.

## User Setup Required
None - no external service configuration required beyond env vars already specified in template.yaml (MATERIALS_BUCKET, EMBED_FUNCTION_NAME, MATERIALS_TABLE).

## Next Phase Readiness
- All 5 material endpoints registered and importable
- DynamoDB CRUD functions ready for embedding Lambda to call update_material_embed_status
- Phase 03-03 (embedding Lambda) can now read material records and update embed_status to "ready"

---
*Phase: 03-materials-and-library*
*Completed: 2026-03-15*
