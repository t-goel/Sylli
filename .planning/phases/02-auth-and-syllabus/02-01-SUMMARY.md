---
phase: 02-auth-and-syllabus
plan: "01"
subsystem: auth
tags: [jwt, pyjwt, passlib, bcrypt, dynamodb, fastapi, lambda]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: DynamoDB infrastructure, FastAPI app structure, SAM template base
provides:
  - UsersTable DynamoDB resource (sylli-users-table, username PK)
  - store_user and get_user_by_username functions in dynamo_service
  - register_user and login_user async functions in auth_service (bcrypt PIN hash, HS256 JWT)
  - get_current_user FastAPI dependency in middleware/auth.py (401 on invalid/expired token)
  - JWT_SECRET and USERS_TABLE env vars on SylliFunction
  - DynamoDB read/write IAM policies for users table
affects:
  - 02-auth-and-syllabus (plan 02 - auth API endpoints will import from auth_service and middleware/auth)
  - All subsequent plans that require authenticated routes

# Tech tracking
tech-stack:
  added:
    - PyJWT (JWT encoding/decoding)
    - passlib[bcrypt] (PIN hashing with bcrypt)
    - bcrypt<4.0 (passlib 1.7.4 compatibility pin)
  patterns:
    - FastAPI dependency injection for auth (get_current_user as Depends())
    - Conditional DynamoDB write with attribute_not_exists for uniqueness enforcement
    - async auth service functions (register_user, login_user)
    - HS256 JWT with user_id + username payload, 7-day expiry
    - login_user returns None on failure (not exception), register_user raises ValueError

key-files:
  created:
    - backend/services/auth_service.py
    - backend/middleware/auth.py
    - backend/middleware/__init__.py
    - backend/tests/test_task1_infra.py
    - backend/tests/test_task2_auth.py
    - backend/tests/__init__.py
  modified:
    - backend/requirements.txt
    - backend/services/dynamo_service.py
    - template.yaml

key-decisions:
  - "bcrypt<4.0 pinned in requirements.txt — passlib 1.7.4 incompatible with bcrypt 5.x due to password-length check in detect_wrap_bug"
  - "login_user returns None on bad credentials (not exception) — avoids caller needing try/except for normal invalid login flow"
  - "register_user raises ValueError for duplicate username — consistent with DynamoDB conditional write behavior"
  - "JWT payload contains both user_id (UUID) and username — user_id is the stable data partition key, username is for display"

patterns-established:
  - "Auth dependency pattern: get_current_user via FastAPI Depends() injects user_id string into route handlers"
  - "PIN validation pattern: 4-8 digits only, validated before hashing"
  - "DynamoDB uniqueness: attribute_not_exists(pk) ConditionExpression raises ValueError on collision"

requirements-completed:
  - AUTH-01
  - AUTH-02
  - AUTH-03

# Metrics
duration: 14min
completed: 2026-03-14
---

# Phase 02 Plan 01: Auth Foundation Summary

**PyJWT + passlib bcrypt auth foundation with DynamoDB users table, register/login service, and FastAPI get_current_user dependency**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-14T19:51:26Z
- **Completed:** 2026-03-14T20:05:43Z
- **Tasks:** 2 (TDD: 4 commits — 2 RED + 2 GREEN)
- **Files modified:** 9

## Accomplishments

- UsersTable DynamoDB resource with username PK, plus read/write IAM policies and env vars wired into SylliFunction
- auth_service.py with register_user (input validation, bcrypt hash, conditional DynamoDB write, JWT) and login_user (hash verification, JWT or None)
- middleware/auth.py with get_current_user FastAPI dependency that decodes HS256 JWT and returns user_id, raising HTTP 401 for invalid/expired tokens
- 28 TDD tests covering all auth behaviors, including mock-based DynamoDB tests and JWT decode edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Auth dependency and infra tests** - `511ec4c` (test)
2. **Task 1 GREEN: Auth dependencies and users table infrastructure** - `5cbcf7f` (feat)
3. **Task 2 RED: Auth service, dynamo user ops, and middleware tests** - `50f46da` (test)
4. **Task 2 GREEN: User DynamoDB operations, auth service, and auth middleware** - `4fc83e3` (feat)

_Note: TDD tasks have multiple commits (test RED → feat GREEN)_

## Files Created/Modified

- `backend/requirements.txt` - Added PyJWT, passlib[bcrypt], bcrypt<4.0
- `template.yaml` - Added UsersTable resource, USERS_TABLE/JWT_SECRET env vars, DynamoDB policies for users table
- `backend/services/dynamo_service.py` - Added store_user (conditional write) and get_user_by_username
- `backend/services/auth_service.py` - Created: register_user, login_user, _create_token with bcrypt and HS256 JWT
- `backend/middleware/__init__.py` - Created: empty package file
- `backend/middleware/auth.py` - Created: get_current_user FastAPI dependency
- `backend/tests/__init__.py` - Created: test package
- `backend/tests/test_task1_infra.py` - Created: 8 tests for infra config verification
- `backend/tests/test_task2_auth.py` - Created: 20 tests for auth service, dynamo ops, and middleware

## Decisions Made

- Pinned bcrypt<4.0 because passlib 1.7.4 (latest stable) calls `detect_wrap_bug` internally using a 200-byte string, which bcrypt 5.x rejects with "password cannot be longer than 72 bytes". The pin ensures Lambda runtime compatibility.
- login_user returns None (not exception) on bad credentials — cleaner flow for caller (no try/except needed for normal invalid-login case).
- JWT payload includes both user_id (UUID, stable partition key for data) and username (for display without extra DynamoDB lookup).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test path calculation (PROJECT_ROOT too deep by one level)**
- **Found during:** Task 1 RED
- **Issue:** Test file computed PROJECT_ROOT as three levels up from test file instead of two, causing FileNotFoundError on requirements.txt and template.yaml
- **Fix:** Changed `"..", "..", ".."` to `"..", ".."` in `os.path.abspath(os.path.join(os.path.dirname(__file__), ...))`
- **Files modified:** backend/tests/test_task1_infra.py
- **Verification:** All 8 tests passed after fix
- **Committed in:** 511ec4c (Task 1 RED commit)

**2. [Rule 3 - Blocking] Installed pytest-asyncio and boto3 for test runner**
- **Found during:** Task 2 RED
- **Issue:** pytest-asyncio needed for `@pytest.mark.asyncio` tests; boto3/botocore needed to import dynamo_service in tests
- **Fix:** Installed pytest-asyncio, boto3 via pip3 --break-system-packages
- **Files modified:** None (local dev environment only)
- **Verification:** 20 tests ran successfully after install
- **Committed in:** N/A (dev environment setup)

**3. [Rule 3 - Blocking] Pinned bcrypt<4.0 to fix passlib + bcrypt 5.x incompatibility**
- **Found during:** Task 2 GREEN (first test run)
- **Issue:** passlib 1.7.4 detect_wrap_bug uses 200-byte test string; bcrypt 5.x rejects passwords > 72 bytes with ValueError — 4 tests failed
- **Fix:** Downgraded bcrypt from 5.0.0 to 3.2.2 locally; added `bcrypt<4.0` pin to requirements.txt
- **Files modified:** backend/requirements.txt
- **Verification:** All 20 tests pass with bcrypt 3.2.2
- **Committed in:** 4fc83e3 (Task 2 GREEN commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All auto-fixes necessary for test correctness and runtime compatibility. No scope creep.

## Issues Encountered

- passlib 1.7.4 + bcrypt 5.x incompatibility is a known upstream issue. The `bcrypt<4.0` pin resolves it for now. When passlib 2.x releases, this constraint can be lifted.

## User Setup Required

None - no external service configuration required beyond what SAM deploys.

## Next Phase Readiness

- Auth foundation complete: get_current_user dependency is ready to protect any route
- Plan 02 (auth API endpoints) can now implement /auth/register and /auth/login using auth_service directly
- Syllabus routes in Plan 03+ will use `Depends(get_current_user)` to scope data by user_id

---
*Phase: 02-auth-and-syllabus*
*Completed: 2026-03-14*

## Self-Check: PASSED

All files and commits verified:
- backend/services/auth_service.py: FOUND
- backend/middleware/auth.py: FOUND
- backend/middleware/__init__.py: FOUND
- backend/tests/test_task2_auth.py: FOUND
- .planning/phases/02-auth-and-syllabus/02-01-SUMMARY.md: FOUND
- Commit 511ec4c (test RED Task 1): FOUND
- Commit 5cbcf7f (feat GREEN Task 1): FOUND
- Commit 50f46da (test RED Task 2): FOUND
- Commit 4fc83e3 (feat GREEN Task 2): FOUND
