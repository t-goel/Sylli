---
phase: 05-quiz-generator
plan: "01"
subsystem: api
tags: [bedrock, rag, quiz, s3vectors, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 04-ai-tutor
    provides: retrieve_chunks(), embed_text(), bedrock client, get_material(), get_presigned_url(), get_current_user() — all reused directly

provides:
  - quiz_service.generate_quiz() — embed query, retrieve chunks, call Bedrock for structured JSON, attach per-question citations
  - POST /api/v1/quiz/generate endpoint with JWT auth, week scoping, and configurable question count
  - QuizResponse with full Question and Citation Pydantic models
affects:
  - 05-quiz-generator (frontend will consume POST /api/v1/quiz/generate)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Quiz RAG pipeline mirrors tutor RAG pipeline: embed → retrieve_chunks → Bedrock converse → parse JSON → attach citations"
    - "Generic embedding query ('key concepts, definitions, and important topics') used instead of user question for quiz generation"
    - "material_id label injected into context block so Bedrock can echo it back per question for citation lookup"
    - "url_cache dict keyed by material_id avoids repeated DynamoDB/S3 lookups within a single quiz response"

key-files:
  created:
    - backend/services/quiz_service.py
    - backend/routers/quiz.py
  modified:
    - backend/app.py

key-decisions:
  - "Generic embed query ('key concepts, definitions, and important topics') used for quiz — no user question available; retrieves broad coverage of material"
  - "top_k capped at min(count*2, 20) — provides 2x chunks per question for variety while preventing Bedrock timeout on large quizzes"
  - "Per-question material_id labels injected via [material_id: ...] syntax in context block — Bedrock echoes them back, enabling O(1) citation lookup from url_cache"
  - "url_cache dict in _attach_citations prevents repeated DynamoDB + S3 calls for questions sharing the same source material"
  - "JSON fence stripping (split on first newline, rsplit on ```) matches existing bedrock_service pattern from tutor_service"

patterns-established:
  - "Quiz service: separate _build_context_block() and _attach_citations() helpers keep generate_quiz() readable"
  - "Bedrock JSON-only mode: system prompt instructs no markdown fences; fence stripping is defensive fallback"

requirements-completed:
  - QUIZ-01
  - QUIZ-02
  - QUIZ-03

# Metrics
duration: 2min
completed: 2026-03-16
---

# Phase 5 Plan 01: Quiz Generator Backend Summary

**RAG quiz pipeline using Bedrock converse with per-question material_id citations, scoped by week or all-materials via POST /api/v1/quiz/generate**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-16T22:59:33Z
- **Completed:** 2026-03-16T23:00:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- quiz_service.generate_quiz() implements full RAG pipeline: embed generic query, retrieve chunks with week filter, build labeled context block, call Bedrock converse, parse JSON array, attach per-question citations with DynamoDB+S3 url_cache
- POST /api/v1/quiz/generate endpoint with JWT auth, QuizRequest (week_number, count), QuizResponse (list of Question with Citation) Pydantic models
- app.py updated to register quiz router at /api/v1 prefix alongside existing routers

## Task Commits

Each task was committed atomically:

1. **Task 1: quiz_service.py — RAG pipeline + Bedrock structured JSON + per-question citations** - `5304dd4` (feat)
2. **Task 2: quiz router + app.py registration** - `db77d3c` (feat)

## Files Created/Modified
- `backend/services/quiz_service.py` - generate_quiz() with embed, retrieve, Bedrock converse, JSON parse, citation attachment
- `backend/routers/quiz.py` - FastAPI router with POST /quiz/generate, QuizRequest/QuizResponse/Question/Citation Pydantic models
- `backend/app.py` - Added quiz import and include_router at /api/v1

## Decisions Made
- Generic embedding query used for quiz generation since there is no user question — retrieves broad coverage across uploaded materials
- top_k capped at min(count*2, 20): gives Bedrock enough variety per question while preventing timeout on large quizzes
- material_id labels injected into context block so Bedrock echoes them faithfully per question, enabling O(1) citation lookup from url_cache
- url_cache dict in _attach_citations prevents N repeated DynamoDB calls when multiple questions share the same source material

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. SylliFunction already has all required IAM permissions (s3vectors:QueryVectors, s3vectors:GetVectors, bedrock:InvokeModel) from prior phases.

## Next Phase Readiness
- Backend quiz generation endpoint fully implemented and verified (import check + route registration confirmed)
- Frontend can POST to /api/v1/quiz/generate with { week_number: N | null, count: 5|10|15 } and receive { questions: [...] }
- No blockers for Phase 05 Plan 02 (quiz frontend)

---
*Phase: 05-quiz-generator*
*Completed: 2026-03-16*
