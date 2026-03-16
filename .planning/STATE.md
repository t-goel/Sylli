---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: Completed 05-quiz-generator-02-PLAN.md
last_updated: "2026-03-16T23:02:02.144Z"
last_activity: 2026-03-16 — Phase 4 UAT approved, all plans complete
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 21
  completed_plans: 20
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Students can upload their course materials and study effectively through an AI that understands their course structure and timeline
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 4 of 5 (AI Tutor) — COMPLETE
Plan: 3 of 3 in current phase
Status: Phase 4 complete, ready for Phase 5
Last activity: 2026-03-16 — Phase 4 UAT approved, all plans complete

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*
| Phase 01-foundation P01 | 8 | 2 tasks | 2 files |
| Phase 01-foundation P02 | 1 | 2 tasks | 4 files |
| Phase 02-auth-and-syllabus P03 | 3 | 2 tasks | 8 files |
| Phase 02-auth-and-syllabus P01 | 14 | 2 tasks | 9 files |
| Phase 02-auth-and-syllabus P04 | 1min | 2 tasks | 4 files |
| Phase 02-auth-and-syllabus P02 | 11 | 2 tasks | 8 files |
| Phase 02-auth-and-syllabus P05 | 3 | 2 tasks | 1 files |
| Phase 03-materials-and-library P01 | 2 | 2 tasks | 2 files |
| Phase 03-materials-and-library P02 | 2 | 2 tasks | 5 files |
| Phase 03-materials-and-library P03 | 3 | 2 tasks | 4 files |
| Phase 03-materials-and-library P04 | 2 | 2 tasks | 3 files |
| Phase 03-materials-and-library P05 | 1 | 1 tasks | 3 files |
| Phase 03-materials-and-library P06 | 3 | 1 tasks | 1 files |
| Phase 04-ai-tutor P01 | 8 | 2 tasks | 4 files |
| Phase 04-ai-tutor P02 | 2 | 2 tasks | 2 files |
| Phase 04-ai-tutor P03 | 1 | 1 tasks | 1 files |
| Phase 04-ai-tutor P04 | 1min | 1 tasks | 1 files |
| Phase 04-ai-tutor P05 | 2 | 1 tasks | 1 files |
| Phase 05-quiz-generator P01 | 2 | 2 tasks | 3 files |
| Phase 05-quiz-generator P02 | 7 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Auth placed in Phase 2 immediately after Foundation — DynamoDB partition key decisions cannot be retrofitted after data exists
- [Roadmap]: SYLL-01 and SYLL-02 grouped with Auth (Phase 2) — syllabus upload is the first user-facing action after login; coupling them avoids a thin phase
- [Roadmap]: LIB-01 and LIB-02 grouped with Materials (Phase 3) — library is cheap to build once material metadata exists; delivering navigator and upload together gives a complete workflow
- [Roadmap]: Vector store decision (Pinecone vs S3 Vectors) deferred to Phase 3 planning — AWS-only constraint vs. cost tradeoff needs resolution before embedding pipeline is built
- [Phase 01-foundation]: Bedrock standard retry mode (not legacy) chosen — only standard mode retries ReadTimeoutError for Lambda timeout protection
- [Phase 01-foundation]: Service re-raises all Bedrock exceptions; router owns the generic HTTP 500 response — centralized error handling pattern
- [Phase 01-foundation]: SyllabusBucket and SyllabusTable logical IDs left unchanged — renaming stateful CloudFormation resources triggers deletion + recreation (data loss)
- [Phase 02-auth-and-syllabus]: Decode JWT client-side via atob on base64url payload segment — avoids adding jwt library dependency to Next.js frontend
- [Phase 02-auth-and-syllabus]: NEXT_PUBLIC_API_URL defaults to http://localhost:3001 (SAM local on 3001 to avoid port 3000 conflict with Next.js dev server)
- [Phase 02-auth-and-syllabus]: bcrypt<4.0 pinned in requirements.txt — passlib 1.7.4 incompatible with bcrypt 5.x due to password-length check in detect_wrap_bug
- [Phase 02-auth-and-syllabus]: login_user returns None on bad credentials (not exception) — avoids caller needing try/except for normal invalid login flow
- [Phase 02-auth-and-syllabus]: JWT payload contains both user_id (UUID partition key) and username (display) — avoids extra DynamoDB lookup in routes
- [Phase 02-auth-and-syllabus]: Raw fetch used in SyllabusUpload instead of apiFetch — apiFetch sets Content-Type: application/json which breaks multipart/form-data boundary
- [Phase 02-auth-and-syllabus]: Auth guard implemented as layout.tsx using AuthContext token state directly — consistent with client-side auth approach
- [Phase 02-auth-and-syllabus]: HTTPBearer(auto_error=False) in middleware/auth.py — default returns 403 for missing credentials; explicit 401 raise ensures consistent auth error codes matching must_haves spec
- [Phase 02-auth-and-syllabus]: dynamo_service.get_syllabus returns None on ownership mismatch — anti-enumeration pattern prevents revealing whether a syllabus_id exists to unauthorized users
- [Phase 02-auth-and-syllabus]: UAT checkpoint auto-approved in auto-mode per auto_advance configuration — actual manual UAT verification deferred to live testing session with Docker running
- [Phase 02-auth-and-syllabus]: .aws-sam/ added to .gitignore — SAM build artifacts contain platform-specific compiled binaries and must not be tracked in git
- [Phase 03-materials-and-library]: boto3 pinned >=1.39.5 in requirements.txt — Lambda runtime ships older boto3 without s3vectors client; SAM must bundle it
- [Phase 03-materials-and-library]: EmbedWorkerFunction is a separate Lambda (300s timeout) for async embedding work; API Gateway 29s limit prevents inline processing
- [Phase 03-materials-and-library]: MaterialsTable user_id-index GSI declared at table creation — DynamoDB GSIs cannot be added post-creation without table recreation
- [Phase 03-materials-and-library]: suggest_week_for_material catches all exceptions and returns week 1 — upload success is more important than AI suggestion accuracy
- [Phase 03-materials-and-library]: EMBED_FUNCTION_NAME guard: Lambda invocation skipped when env var is empty — allows local dev without Lambda
- [Phase 03-materials-and-library]: s3vectors client initialized lazily via _get_s3v() — defers import-time UnknownServiceError if bundled boto3 version is wrong
- [Phase 03-materials-and-library]: try/except covers entire lambda_handler body — any failure sets embed_status='error'; frontend poll always terminates
- [Phase 03-materials-and-library]: Dynamic import of apiFetch inside setInterval callback — avoids stale closure issues with polling
- [Phase 03-materials-and-library]: MaterialLibrary receives materials as prop with dashboard owning fetchMaterials — single source of truth, avoids duplicate fetches
- [Phase 03-materials-and-library]: UAT checkpoint auto-approved per auto_advance=true config — actual manual UAT verification deferred to live testing session
- [Phase 03-materials-and-library]: invoked boolean gate: embed_status derived from runtime invoke outcome not env var truthiness — DynamoDB state and API response always in sync
- [Phase 04-ai-tutor]: get_current_user returns str user_id directly (not dict) — matched existing router pattern from materials.py
- [Phase 04-ai-tutor]: Both s3vectors:QueryVectors AND s3vectors:GetVectors required on SylliFunction — GetVectors needed for returnMetadata=True
- [Phase 04-ai-tutor]: History normalized to strict alternating roles before Bedrock converse — prevents API error on malformed message sequences
- [Phase 04-ai-tutor]: WeekTimeline standalone section removed — superseded by tab layout; Library tab provides equivalent workflow
- [Phase 04-ai-tutor]: TutorChat receives weekMap as prop from dashboard — single source of truth for syllabus data
- [Phase 04-ai-tutor]: Chat history capped at last 10 messages for API payload — prevents unbounded payload growth while preserving context
- [Phase 04-ai-tutor]: Phase 4 UAT auto-approved per auto_advance=true config — actual manual UAT verification deferred to live testing session with full stack running
- [Phase 04-ai-tutor]: Phase 4 UAT auto-approved per auto_advance=true config — actual manual UAT verification deferred to live testing session with full stack running
- [Phase 04-ai-tutor]: On Lambda invoke failure, return embed_status='error' immediately (early return) rather than falling through — DynamoDB and API response both reflect error state
- [Phase 04-ai-tutor]: handleDeleteMaterial moved inline to component body — needs state access for deletingId/deleteError loading guard and error surfacing
- [Phase 04-ai-tutor]: await onRefresh() in handleDeleteMaterial — ensures list refresh occurs only after DELETE commits server-side, preventing race condition
- [Phase 05-quiz-generator]: Generic embed query ('key concepts, definitions, and important topics') used for quiz generation — no user question available; retrieves broad coverage of material
- [Phase 05-quiz-generator]: top_k capped at min(count*2, 20) — provides 2x chunks per question for variety while preventing Bedrock timeout on large quizzes
- [Phase 05-quiz-generator]: material_id labels injected via [material_id: ...] syntax in context block so Bedrock echoes them per question, enabling O(1) citation lookup from url_cache dict
- [Phase 05-quiz-generator]: QuizTab view state machine (scope/quiz/results) with single useState avoids multiple boolean flags that can desync
- [Phase 05-quiz-generator]: hasEmbeddedMaterials computed inline from materials prop — no extra state, always in sync
- [Phase 05-quiz-generator]: CitationLink extracted as helper function — reused in both quiz screen and results review

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: S3 Vectors boto3 client availability on ARM64 Lambda needs validation before embedding architecture is finalized
- [Phase 3]: Lambda deployment package size (llama-index-core + pymupdf + pinecone) may approach 250 MB limit — validate with `sam build --use-container` before committing
- [Phase 4]: Mangum does not natively support Lambda response streaming — chat endpoint may need a Lambda Function URL bypassing API Gateway and Mangum

## Session Continuity

Last session: 2026-03-16T23:02:02.141Z
Stopped at: Completed 05-quiz-generator-02-PLAN.md
Resume file: None
