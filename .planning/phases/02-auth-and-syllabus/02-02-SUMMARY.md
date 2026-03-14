---
phase: 02-auth-and-syllabus
plan: "02"
subsystem: auth-api
tags: [fastapi, jwt, cors, dynamo, auth-enforcement, syllabus, tdd]

# Dependency graph
requires:
  - phase: 02-auth-and-syllabus
    plan: "01"
    provides: auth_service, middleware/auth.py, get_current_user dependency
provides:
  - POST /api/v1/auth/register endpoint (200+token or 409 on duplicate)
  - POST /api/v1/auth/login endpoint (200+token or 401 on wrong PIN)
  - CORSMiddleware on app allowing http://localhost:3000 and *.amplifyapp.com
  - Syllabus routes auth-gated with get_current_user Depends injection
  - dynamo_service.store_syllabus now scoped by user_id
  - dynamo_service.get_syllabus now validates ownership (returns None on mismatch)
affects:
  - frontend auth flows (register/login API now consumable)
  - all subsequent syllabus data access (scoped by user_id partition)

# Tech tracking
tech-stack:
  added:
    - fastapi.middleware.cors.CORSMiddleware (CORS configuration)
  patterns:
    - FastAPI HTTPBearer(auto_error=False) to return 401 (not 403) for missing Authorization
    - Route-level auth injection via Depends(get_current_user) on POST and GET syllabus routes
    - user_id ownership check in DynamoDB read returning None (not 403) to prevent enumeration
    - user_id forwarded through service layer (router -> service -> dynamo)
    - Auth router with Pydantic AuthRequest model, ValueError -> HTTPException(409) mapping

key-files:
  created:
    - backend/routers/auth.py
    - backend/tests/test_task3_auth_router.py
    - backend/tests/test_task4_syllabus_auth.py
  modified:
    - backend/app.py
    - backend/routers/syllabus.py
    - backend/services/dynamo_service.py
    - backend/services/syllabus_service.py
    - backend/middleware/auth.py

key-decisions:
  - "HTTPBearer(auto_error=False) used in middleware/auth.py — default auto_error=True raises 403 on missing credentials; auto_error=False allows manual 401 raise, matching must_haves spec"
  - "dynamo_service.get_syllabus returns None (not HTTPException 403) on ownership mismatch — avoids confirming item existence to unauthorized requesters (anti-enumeration pattern)"
  - "CORSMiddleware allows both http://localhost:3000 (Next.js dev) and https://*.amplifyapp.com (Amplify production) — covers full dev-to-prod cycle without additional config changes"

patterns-established:
  - "Auth-gated route pattern: user_id: str = Depends(get_current_user) in route signature, forwarded as keyword arg to service"
  - "Service layer user_id threading: router passes user_id to service, service passes to dynamo — single responsibility at each layer"

requirements-completed:
  - SYLL-01

# Metrics
duration: 11min
completed: 2026-03-14
---

# Phase 02 Plan 02: Auth API Endpoints and Syllabus Auth Enforcement Summary

**FastAPI auth router (register/login) with CORS, syllabus routes auth-gated via Depends(get_current_user), and DynamoDB operations scoped by user_id**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-03-14T19:49:00Z
- **Completed:** 2026-03-14T20:01:46Z
- **Tasks:** 2 (TDD: 4 commits — 2 RED + 2 GREEN)
- **Files modified:** 8

## Accomplishments

- auth.py router with POST /api/v1/auth/register (200+token, 409 duplicate) and POST /api/v1/auth/login (200+token, 401 wrong PIN)
- app.py updated with CORSMiddleware allowing localhost:3000 and *.amplifyapp.com, auth router registered at /api/v1
- syllabus.py router now injects `get_current_user` via Depends on both POST and GET routes, passes user_id to service layer
- dynamo_service.store_syllabus and get_syllabus updated with user_id parameter — get_syllabus returns None on ownership mismatch (anti-enumeration)
- syllabus_service.upload_syllabus_to_s3 and fetch_syllabus updated to accept and forward user_id
- middleware/auth.py fixed to return 401 (not 403) when no Authorization header present
- 28 new TDD tests across 2 test files — 56 total tests passing across all test files

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Auth router and CORS tests** - `c14f003` (test)
2. **Task 1 GREEN: Auth router and app.py CORS** - `1a7685e` (feat)
3. **Task 2 RED: Syllabus auth enforcement and user_id scoping tests** - `bf8ca39` (test)
4. **Task 2 GREEN: User_id enforcement on syllabus routes and DynamoDB** - `55795c3` (feat)

_Note: TDD tasks have multiple commits (test RED → feat GREEN)_

## Files Created/Modified

- `backend/routers/auth.py` - Created: POST /auth/register and POST /auth/login with Pydantic AuthRequest model
- `backend/app.py` - Added CORSMiddleware (localhost:3000, *.amplifyapp.com) and auth router at /api/v1
- `backend/routers/syllabus.py` - Added Depends(get_current_user) to both routes, passes user_id to service
- `backend/services/dynamo_service.py` - store_syllabus now accepts/writes user_id; get_syllabus validates ownership
- `backend/services/syllabus_service.py` - upload_syllabus_to_s3 and fetch_syllabus accept and forward user_id
- `backend/middleware/auth.py` - Changed to HTTPBearer(auto_error=False) to return 401 (not 403) for missing credentials
- `backend/tests/test_task3_auth_router.py` - Created: 13 tests for auth router structure and HTTP behavior
- `backend/tests/test_task4_syllabus_auth.py` - Created: 15 tests for syllabus auth enforcement and user_id scoping

## Decisions Made

- `HTTPBearer(auto_error=False)` + explicit 401 raise in `get_current_user` — FastAPI's default `auto_error=True` returns 403 when no Authorization header present; the plan's `must_haves` requires 401. Auto_error=False allows manual 401 for consistent auth error codes.
- `get_syllabus` returns `None` on ownership mismatch rather than raising 403 — prevents information leakage about whether a syllabus ID exists. Callers see 404 regardless of whether the item exists but belongs to another user.
- CORS configured for both `http://localhost:3000` and `https://*.amplifyapp.com` wildcard — covers Next.js dev server and all Amplify branch preview URLs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed mangum for local test execution**
- **Found during:** Task 1 GREEN (first test run)
- **Issue:** `mangum` is declared in requirements.txt for Lambda but not installed locally; `import app` failed with `ModuleNotFoundError: No module named 'mangum'`
- **Fix:** Installed `mangum==0.21.0` via `pip3 install mangum --break-system-packages`
- **Files modified:** None (local dev environment only)
- **Verification:** All 13 Task 1 tests passed after install
- **Committed in:** N/A (dev environment setup)

**2. [Rule 1 - Bug] Fixed HTTPBearer returning 403 instead of 401 for missing credentials**
- **Found during:** Task 2 GREEN (test run after implementation)
- **Issue:** `HTTPBearer(auto_error=True)` (the default) raises HTTP 403 when no Authorization header is present; plan's `must_haves` specifies 401 for unauthenticated requests
- **Fix:** Changed `security = HTTPBearer()` to `security = HTTPBearer(auto_error=False)` in middleware/auth.py; added explicit `if credentials is None: raise HTTPException(status_code=401, ...)` check
- **Files modified:** `backend/middleware/auth.py`
- **Verification:** All 15 Task 2 tests pass; all 56 total tests still pass
- **Committed in:** 55795c3 (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed items above.

## User Setup Required

None — no external service configuration required beyond what SAM deploys.

## Next Phase Readiness

- Auth API complete: frontend can call POST /api/v1/auth/register and /api/v1/auth/login
- Syllabus routes fully gated: unauthenticated requests return 401, cross-user access returns 404
- CORS configured for Next.js dev server on port 3000
- Plan 03 (syllabus upload E2E) can build on this auth foundation

---
*Phase: 02-auth-and-syllabus*
*Completed: 2026-03-14*

## Self-Check: PASSED

All files and commits verified:
- backend/routers/auth.py: FOUND
- backend/app.py: FOUND
- backend/routers/syllabus.py: FOUND
- backend/services/dynamo_service.py: FOUND
- backend/services/syllabus_service.py: FOUND
- backend/middleware/auth.py: FOUND
- backend/tests/test_task3_auth_router.py: FOUND
- backend/tests/test_task4_syllabus_auth.py: FOUND
- .planning/phases/02-auth-and-syllabus/02-02-SUMMARY.md: FOUND
- Commit c14f003 (test RED Task 1): FOUND
- Commit 1a7685e (feat GREEN Task 1): FOUND
- Commit bf8ca39 (test RED Task 2): FOUND
- Commit 55795c3 (feat GREEN Task 2): FOUND
