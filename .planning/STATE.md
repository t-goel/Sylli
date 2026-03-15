---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed 03-materials-and-library 03-05-PLAN.md
last_updated: "2026-03-15T20:51:48.185Z"
last_activity: 2026-03-14 — Phase 2 UAT approved, ready for Phase 3
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 12
  completed_plans: 12
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Students can upload their course materials and study effectively through an AI that understands their course structure and timeline
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 3 of 5 (Materials and Library)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-14 — Phase 2 UAT approved, ready for Phase 3

Progress: [░░░░░░░░░░] 0%

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: S3 Vectors boto3 client availability on ARM64 Lambda needs validation before embedding architecture is finalized
- [Phase 3]: Lambda deployment package size (llama-index-core + pymupdf + pinecone) may approach 250 MB limit — validate with `sam build --use-container` before committing
- [Phase 4]: Mangum does not natively support Lambda response streaming — chat endpoint may need a Lambda Function URL bypassing API Gateway and Mangum

## Session Continuity

Last session: 2026-03-15T20:51:42.599Z
Stopped at: Completed 03-materials-and-library 03-05-PLAN.md
Resume file: None
