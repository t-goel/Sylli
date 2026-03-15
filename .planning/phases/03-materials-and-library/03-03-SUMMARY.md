---
phase: 03-materials-and-library
plan: "03"
subsystem: embedding-pipeline
tags: [lambda, bedrock, s3vectors, pymupdf, python-pptx, tdd, chunking, titan-embed]

# Dependency graph
requires:
  - phase: 03-materials-and-library
    plan: "01"
    provides: EmbedWorkerFunction Lambda, s3vectors IAM, MATERIALS_BUCKET env var
  - phase: 03-materials-and-library
    plan: "02"
    provides: get_material, update_material_embed_status in dynamo_service.py

provides:
  - backend/services/embedding_service.py (extract_text, chunk_text, embed_text, write_vectors_to_s3)
  - backend/workers/embed_worker.py (lambda_handler for async embedding job)
  - backend/workers/__init__.py (Python package declaration)
  - backend/tests/test_embedding_service.py (15 TDD tests)

affects:
  - 03-04 (Phase 4 chat can now query S3 Vectors for material chunks by week_number/user_id)
  - All frontend polling on /api/v1/materials/{id}/status — guaranteed to terminate

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD RED-GREEN-REFACTOR for service functions
    - Lazy s3vectors client initialization to avoid import-time errors on older boto3
    - AWS_REGION_NAME custom env var pattern (avoids Lambda reserved AWS_REGION conflict)
    - Fixed-size chunking with overlap (1500-char window, 200-char overlap)
    - Try/except wrapping full Lambda body to guarantee terminal status ('ready' or 'error')

key-files:
  created:
    - backend/services/embedding_service.py
    - backend/workers/embed_worker.py
    - backend/workers/__init__.py
    - backend/tests/test_embedding_service.py
  modified: []

key-decisions:
  - "s3vectors client initialized lazily via _get_s3v() — defers import-time UnknownServiceError if bundled boto3 version is wrong; fails at call time with clear error instead"
  - "try/except covers entire lambda_handler body — any failure (DynamoDB read, S3 download, text extraction, Bedrock call, S3 Vectors write) sets embed_status='error'; frontend poll always terminates"
  - "extract_text imports fitz and pptx locally (inside function) — isolates heavy dependencies from module-level; avoids circular import issues"

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 3 Plan 03: Embedding Pipeline Summary

**Async Lambda embedding pipeline: text extraction (PDF/PPTX via PyMuPDF/python-pptx), 1500-char overlapping chunks, Titan Embed V2 via Bedrock, and S3 Vectors write with user/material/week metadata — guaranteed to terminate DynamoDB poll via try/except covering entire handler body**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T20:43:21Z
- **Completed:** 2026-03-15T20:45:39Z
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- Created `embedding_service.py` with four pure functions (TDD): `extract_text`, `chunk_text`, `embed_text`, `write_vectors_to_s3`
- Created `workers/__init__.py` making workers a Python package for SAM handler path resolution
- Created `workers/embed_worker.py` with full embedding pipeline: DynamoDB lookup → S3 download → text extract → chunk → embed → S3 Vectors write → status update
- Written 15 tests in `test_embedding_service.py` covering all behaviors (mocked boto3)

## Task Commits

Each task was committed atomically:

1. **Task 1 TDD RED: Add failing tests for embedding_service** - `4005cff` (test)
2. **Task 1 TDD GREEN: Implement embedding_service.py** - `6d5d763` (feat)
3. **Task 2: Create embed worker Lambda handler** - `2e99bab` (feat)

**Plan metadata:** *(docs commit follows)*

## Files Created/Modified

- `backend/services/embedding_service.py` — extract_text (PDF/PPTX), chunk_text (1500/200 overlap), embed_text (Titan V2), write_vectors_to_s3
- `backend/workers/__init__.py` — empty init for Python package
- `backend/workers/embed_worker.py` — lambda_handler with full pipeline and guaranteed terminal status
- `backend/tests/test_embedding_service.py` — 15 tests covering all four functions with mocked boto3

## Decisions Made

- s3vectors client initialized lazily via `_get_s3v()` — defers import-time UnknownServiceError if bundled boto3 version is wrong; fails at call time with a clear error instead of at cold start
- `try/except` covers entire `lambda_handler` body — any failure at any pipeline stage sets `embed_status='error'`; frontend poll always terminates without getting stuck on 'processing'
- `extract_text` imports `fitz` and `pptx` inside the function body — isolates heavy dependencies, avoids module-level import failures during Lambda cold start if the dependency is missing

## Deviations from Plan

None - plan executed exactly as written.

`get_material` and `update_material_embed_status` were already present in `dynamo_service.py` from a prior 03-02 execution; no additional changes were needed.

## User Setup Required

None.

## Next Phase Readiness

- Embedding pipeline is fully implemented and tested
- Phase 4 can query S3 Vectors by `user_id` and `week_number` metadata filters
- Frontend polling on `/api/v1/materials/{id}/status` is guaranteed to terminate (no infinite poll)
- Workers package importable at `workers.embed_worker.lambda_handler` as declared in template.yaml

---
*Phase: 03-materials-and-library*
*Completed: 2026-03-15*
