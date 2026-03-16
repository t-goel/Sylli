---
phase: 04-ai-tutor
plan: "01"
subsystem: api
tags: [bedrock, s3vectors, rag, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 03-materials-and-library
    provides: embedding_service with embed_text/_get_s3v, vectors written to S3 Vectors with user_id/material_id/week_number metadata
  - phase: 03-materials-and-library
    provides: material_service.get_presigned_url and dynamo_service.get_material for citation assembly
provides:
  - RAG pipeline in tutor_service.py (embed query -> query_vectors -> generate answer -> build citations)
  - POST /api/v1/tutor/chat endpoint with JWT auth, typed request/response, week filter support
  - S3 Vectors IAM query permissions on SylliFunction (QueryVectors + GetVectors)
affects: [04-ai-tutor-frontend, future phases using tutor API]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RAG pipeline: embed query -> similarity search -> short-circuit on empty -> Bedrock generate -> citation assembly"
    - "History normalization: drop leading assistant messages, collapse consecutive same-role entries"
    - "Zero-chunk short-circuit: return helpful message without invoking Bedrock"

key-files:
  created:
    - backend/services/tutor_service.py
    - backend/routers/tutor.py
  modified:
    - backend/app.py
    - template.yaml

key-decisions:
  - "get_current_user returns str user_id directly (not dict) — matched existing router pattern from materials.py"
  - "Both s3vectors:QueryVectors AND s3vectors:GetVectors required on SylliFunction — GetVectors needed for returnMetadata=True"
  - "Reuse bedrock client and MODEL_ID from bedrock_service — no second boto3 client created"
  - "History normalized to strict alternating roles before Bedrock converse — prevents API error on malformed message sequences"

patterns-established:
  - "Router pattern: APIRouter with prefix on the router itself, registered at /api/v1 in app.py"
  - "Auth pattern: user_id: str = Depends(get_current_user) returning str directly"

requirements-completed: [TUTOR-01, TUTOR-02]

# Metrics
duration: 8min
completed: 2026-03-16
---

# Phase 4 Plan 01: Backend RAG Tutor Pipeline Summary

**RAG chat endpoint with S3 Vectors similarity search, Bedrock Claude generation, and per-material citation assembly using existing embeddings from Phase 3**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-16T20:30:00Z
- **Completed:** 2026-03-16T20:38:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `POST /api/v1/tutor/chat` endpoint that performs full RAG pipeline: embed query with Titan V2, query S3 Vectors filtered by user_id (and optionally week_number), generate answer with Claude via Bedrock, assemble deduplicated citations with presigned S3 URLs
- Zero-chunk short-circuit: when no vectors match, returns helpful "check Library tab" message without invoking Bedrock
- Conversation history normalization ensures strict role alternation before passing to Bedrock converse (prevents API errors)
- SylliFunction granted `s3vectors:QueryVectors` and `s3vectors:GetVectors` with env vars for bucket/index names

## Task Commits

1. **Task 1: IAM permissions and env vars for S3 Vectors** - `c32c046` (chore)
2. **Task 2: tutor_service.py, routers/tutor.py, app.py registration** - `e85439e` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/services/tutor_service.py` - RAG orchestration: retrieve_chunks, build_citations, generate_answer, ask()
- `backend/routers/tutor.py` - POST /tutor/chat with ChatRequest/ChatResponse Pydantic models and JWT auth
- `backend/app.py` - Added tutor router import and include_router at /api/v1
- `template.yaml` - Added s3vectors:QueryVectors, s3vectors:GetVectors policy and VECTOR_BUCKET_NAME/VECTOR_INDEX_NAME/AWS_REGION_NAME env vars to SylliFunction

## Decisions Made
- `get_current_user` returns a `str` (user_id) directly per existing codebase pattern — the plan's interface comment showing a dict was incorrect. Using `user_id: str = Depends(get_current_user)` consistent with materials.py.
- Reused `bedrock` client and `MODEL_ID` from `bedrock_service` — plan explicitly required not creating a second boto3 client.
- Both `s3vectors:QueryVectors` AND `s3vectors:GetVectors` added to SylliFunction — `GetVectors` required when `returnMetadata=True` is set.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected auth dependency signature**
- **Found during:** Task 2 (tutor router creation)
- **Issue:** Plan showed `user: dict = Depends(get_current_user)` with `user["user_id"]` access, but `get_current_user` actually returns `str` user_id directly (verified in middleware/auth.py)
- **Fix:** Used `user_id: str = Depends(get_current_user)` matching actual signature and existing router pattern
- **Files modified:** backend/routers/tutor.py
- **Verification:** `python3 -c "from routers.tutor import router"` passes without error
- **Committed in:** e85439e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan interface description)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Issues Encountered
None beyond the auth signature mismatch fixed above.

## User Setup Required
None - no external service configuration required beyond IAM permissions already added to template.yaml.

## Next Phase Readiness
- Backend RAG endpoint complete and import-verified
- Frontend TutorChat component can now call `POST /api/v1/tutor/chat` with `{question, history, week_number}`
- Citations include `{filename, week_number, url}` shape ready for frontend rendering
- Deployment requires `sam build && sam deploy` to apply new IAM policy and env vars to SylliFunction

---
*Phase: 04-ai-tutor*
*Completed: 2026-03-16*
