---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
stopped_at: Completed 02-auth-and-syllabus-04-PLAN.md
last_updated: "2026-03-14T20:00:09.136Z"
last_activity: 2026-03-14 — Roadmap created, phases derived from requirements
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 7
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Students can upload their course materials and study effectively through an AI that understands their course structure and timeline
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 5 (Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-14 — Roadmap created, phases derived from requirements

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 3]: S3 Vectors boto3 client availability on ARM64 Lambda needs validation before embedding architecture is finalized
- [Phase 3]: Lambda deployment package size (llama-index-core + pymupdf + pinecone) may approach 250 MB limit — validate with `sam build --use-container` before committing
- [Phase 4]: Mangum does not natively support Lambda response streaming — chat endpoint may need a Lambda Function URL bypassing API Gateway and Mangum

## Session Continuity

Last session: 2026-03-14T20:00:09.133Z
Stopped at: Completed 02-auth-and-syllabus-04-PLAN.md
Resume file: None
