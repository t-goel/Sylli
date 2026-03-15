---
phase: 02-auth-and-syllabus
verified: 2026-03-14T21:00:00Z
status: human_needed
score: 16/16 automated must-haves verified
re_verification: false
human_verification:
  - test: "Register a new user via the Next.js UI"
    expected: "Form submits, token stored in localStorage, redirect to /dashboard, username displayed in header"
    why_human: "UAT was auto-approved in auto-mode without Docker running; real end-to-end register flow was never tested in a live environment"
  - test: "Upload a PDF syllabus on the dashboard"
    expected: "Upload completes, parsed week_map renders as a vertical timeline below the upload area with course name and weekly entries"
    why_human: "Requires SAM local backend + Docker Desktop running; confirmed unverified in 02-05-SUMMARY.md"
  - test: "Log out and log back in with the same credentials"
    expected: "Sign out clears localStorage, redirect to /login; sign back in with same username+PIN returns to /dashboard"
    why_human: "Token persistence and re-login flow requires a live DynamoDB instance; never exercised in auto-mode UAT"
  - test: "Cross-user isolation: user B cannot read user A's syllabus"
    expected: "GET /api/v1/syllabus/<user_A_syllabus_id> with user B's token returns 404"
    why_human: "Requires two registered users and a live DynamoDB table; auto-mode skipped this check"
  - test: "Unauthenticated access to syllabus routes"
    expected: "GET or POST /api/v1/syllabus without Authorization header returns 401 (code uses manual 401, not FastAPI's default 403)"
    why_human: "Requires live backend; also validates the auto_error=False deviation from the plan's stated 403 expectation"
---

# Phase 02: Auth and Syllabus Verification Report

**Phase Goal:** Each student has a private account, and after logging in they can upload their course syllabus and see the parsed timeline
**Verified:** 2026-03-14
**Status:** human_needed — all 16 automated must-haves pass; UAT was auto-approved in auto-mode without a live backend
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A user can register with a username and PIN and receive a JWT token | VERIFIED | `auth_service.register_user` hashes PIN with bcrypt, calls `store_user`, returns `_create_token(user_id, username)` |
| 2 | A user can log in with the same credentials and receive the same-subject JWT | VERIFIED | `auth_service.login_user` verifies bcrypt hash, returns `_create_token(user["user_id"], username)` |
| 3 | An invalid username or wrong PIN returns 401 | VERIFIED | `login_user` returns `None`; `routers/auth.py` converts that to `HTTPException(401)` |
| 4 | User data is scoped by user_id — cross-user access returns 404 | VERIFIED | `dynamo_service.get_syllabus` checks `item.get("user_id") != user_id` and returns `None`; router converts to 404 |
| 5 | POST /api/v1/auth/register with valid username+PIN returns 200 with {token} | VERIFIED | `routers/auth.py` POST `/auth/register` returns `{"token": token}` |
| 6 | POST /api/v1/auth/register with duplicate username returns 409 | VERIFIED | `register_user` raises `ValueError("Username already taken")`; router catches and raises `HTTPException(409)` |
| 7 | POST /api/v1/auth/login with wrong PIN returns 401 | VERIFIED | `login_user` returns `None`; router raises `HTTPException(401, "Invalid username or PIN")` |
| 8 | POST /api/v1/syllabus without Authorization header returns 401 | VERIFIED | `HTTPBearer(auto_error=False)` + manual `HTTPException(401)` in `get_current_user` when `credentials is None` |
| 9 | Visiting / redirects to /login when no token is in localStorage | VERIFIED | `app/page.tsx` reads `useAuth().token`; `useEffect` calls `router.replace("/login")` when token is falsy |
| 10 | Login page renders a form with username/PIN fields and mode toggle | VERIFIED | `AuthForm.tsx` has username input, PIN input (type=password, pattern=[0-9]{4,8}), and Login/Register toggle buttons |
| 11 | Successful register/login stores token in localStorage and redirects to /dashboard | VERIFIED | `login/page.tsx` calls `decodeJwtPayload`, then `setAuth(token, user_id, username)` (writes localStorage), then `router.replace("/dashboard")` |
| 12 | useAuth() hook is available throughout app via AuthProvider in root layout | VERIFIED | `layout.tsx` wraps `{children}` in `<AuthProvider>`; `useAuth()` throws if called outside provider |
| 13 | Visiting /dashboard without a token redirects to /login | VERIFIED | `dashboard/layout.tsx` calls `router.replace("/login")` in `useEffect` when `!token`; returns `null` until token confirmed |
| 14 | Uploading a PDF calls POST /api/v1/syllabus with multipart form data and Authorization header | VERIFIED | `SyllabusUpload.tsx` uses raw `fetch` with `FormData`, injects `Authorization: Bearer ${token}` header from `localStorage` |
| 15 | After successful upload, the week/unit timeline is displayed | VERIFIED | `dashboard/page.tsx` sets `weekMap` state from `data.week_map` in `handleUploadSuccess`; conditionally renders `<WeekTimeline weekMap={weekMap} />` |
| 16 | Weeks with missing/undefined notes do not crash the component | VERIFIED | `WeekTimeline.tsx` uses `weekMap?.weeks ?? []`, `w.topic ?? "Untitled"`, `w.readings ?? []`; `w.notes` rendered only when truthy |

**Score:** 16/16 truths verified (automated)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/auth_service.py` | register_user, login_user, _create_token | VERIFIED | All three functions present and substantive; bcrypt hash + HS256 JWT |
| `backend/services/dynamo_service.py` | store_user, get_user_by_username, updated store_syllabus/get_syllabus with user_id | VERIFIED | All four functions present; ownership check on line 34: `item.get("user_id") != user_id` |
| `backend/middleware/auth.py` | get_current_user FastAPI dependency | VERIFIED | Returns user_id string; raises HTTP 401 for missing/invalid/expired token using `algorithms=["HS256"]` list |
| `backend/middleware/__init__.py` | Package init file | VERIFIED | File exists |
| `template.yaml` | UsersTable resource, USERS_TABLE + JWT_SECRET env vars, DynamoDB policies | VERIFIED | UsersTable with `TableName: sylli-users-table`, DynamoDBWritePolicy + DynamoDBReadPolicy for users table, env vars present |
| `backend/requirements.txt` | PyJWT, passlib[bcrypt], bcrypt<4.0 | VERIFIED | Lines 6-8: `PyJWT`, `passlib[bcrypt]`, `bcrypt<4.0` |
| `backend/routers/auth.py` | POST /auth/register and POST /auth/login | VERIFIED | Both routes present; imports from `services.auth_service` |
| `backend/routers/syllabus.py` | upload/get endpoints with user_id enforcement via Depends | VERIFIED | Both routes inject `user_id: str = Depends(get_current_user)` |
| `backend/app.py` | auth router registered, CORSMiddleware configured | VERIFIED | CORSMiddleware with `allow_origins=["http://localhost:3000", "https://*.amplifyapp.com"]`; auth router at `/api/v1` |
| `frontend/context/AuthContext.tsx` | AuthProvider, useAuth, token/user_id/username state | VERIFIED | Exports `AuthProvider` and `useAuth`; persists all three keys to localStorage |
| `frontend/lib/api.ts` | apiFetch with Authorization header injection, decodeJwtPayload | VERIFIED | Both functions exported; apiFetch reads token from localStorage |
| `frontend/components/AuthForm.tsx` | Username+PIN form with register/login mode toggle | VERIFIED | Both inputs rendered; mode toggle buttons wired via `setMode` state |
| `frontend/app/login/page.tsx` | Login page calling apiFetch, decoding JWT, calling setAuth, redirecting | VERIFIED | All four steps present in `handleSubmit` |
| `frontend/app/layout.tsx` | Root layout wrapping children in AuthProvider | VERIFIED | `<AuthProvider>{children}</AuthProvider>` on line 21 |
| `frontend/app/dashboard/layout.tsx` | Auth guard redirecting to /login without token | VERIFIED | `router.replace("/login")` in useEffect; `if (!token) return null` guard |
| `frontend/components/SyllabusUpload.tsx` | File input, raw fetch with FormData and Authorization header | VERIFIED | Uses `new FormData()`, raw `fetch()` (not apiFetch), `Authorization: Bearer ${token}` header |
| `frontend/components/WeekTimeline.tsx` | Renders week_map.weeks with defensive null handling | VERIFIED | Nullish coalescing on all optional fields |
| `frontend/app/dashboard/page.tsx` | Combines SyllabusUpload and WeekTimeline with state | VERIFIED | `handleUploadSuccess` sets `weekMap` state; conditionally renders `<WeekTimeline>` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `backend/services/auth_service.py` | `backend/services/dynamo_service.py` | `from services.dynamo_service import store_user, get_user_by_username` | WIRED | Line 8 of auth_service.py |
| `backend/middleware/auth.py` | `jwt.decode` | `algorithms=["HS256"]` list param | WIRED | Line 22 of middleware/auth.py — list form (not string) |
| `backend/routers/auth.py` | `backend/services/auth_service.py` | `from services.auth_service import register_user, login_user` | WIRED | Line 3 of routers/auth.py |
| `backend/routers/syllabus.py` | `backend/middleware/auth.py` | `Depends(get_current_user)` on both routes | WIRED | Lines 11 and 26 of routers/syllabus.py |
| `backend/services/dynamo_service.py` | user_id ownership check | `item.get("user_id") != user_id` in get_syllabus | WIRED | Line 34 of dynamo_service.py |
| `backend/services/syllabus_service.py` | `dynamo_service.store_syllabus` | Passes `user_id=user_id` keyword arg | WIRED | Line 30-37 of syllabus_service.py |
| `frontend/app/login/page.tsx` | `frontend/lib/api.ts` | `apiFetch('/api/v1/auth/register')` and `apiFetch('/api/v1/auth/login')` | WIRED | Line 19 of login/page.tsx |
| `frontend/app/login/page.tsx` | `frontend/context/AuthContext.tsx` | `useAuth().setAuth(token, user_id, username)` | WIRED | Lines 9 and 29 of login/page.tsx |
| `frontend/app/layout.tsx` | `frontend/context/AuthContext.tsx` | `<AuthProvider>` wrapping `{children}` | WIRED | Line 21 of layout.tsx |
| `frontend/components/SyllabusUpload.tsx` | POST /api/v1/syllabus | `new FormData()` + raw `fetch()` with `Authorization: Bearer` | WIRED | Lines 26-42 of SyllabusUpload.tsx |
| `frontend/app/dashboard/page.tsx` | `frontend/components/WeekTimeline.tsx` | `weekMap` state set from upload response, passed as prop | WIRED | Lines 24-25 (setState) and line 54 (prop) of dashboard/page.tsx |
| `frontend/app/dashboard/layout.tsx` | `frontend/context/AuthContext.tsx` | `useAuth().token` check in useEffect | WIRED | Lines 7 and 11 of dashboard/layout.tsx |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| AUTH-01 | 02-01, 02-02, 02-03, 02-05 | User can create a session by entering a username and PIN | SATISFIED | `auth_service.register_user` + `auth_service.login_user` + `/auth/register` + `/auth/login` routes + AuthForm UI all present and wired |
| AUTH-02 | 02-01, 02-02, 02-05 | User's data is scoped to their username | SATISFIED | `dynamo_service.get_syllabus` enforces `item["user_id"] == user_id`; `store_syllabus` writes `user_id`; cross-user access returns `None` (→ 404) |
| AUTH-03 | 02-01, 02-02, 02-03, 02-05 | User can log out and return with the same username+PIN to access their data | SATISFIED (automated) / NEEDS HUMAN (live) | Logout clears localStorage; re-login re-fetches token via `login_user` from DynamoDB. Live re-login path not UAT-verified |
| SYLL-01 | 02-02, 02-04, 02-05 | User can upload a course syllabus PDF through the UI | SATISFIED (automated) / NEEDS HUMAN (live) | `SyllabusUpload.tsx` sends multipart FormData with Bearer token; backend route accepts via `Depends(get_current_user)` |
| SYLL-02 | 02-04, 02-05 | User can view the parsed week/unit timeline after syllabus upload | SATISFIED (automated) / NEEDS HUMAN (live) | `WeekTimeline.tsx` renders `week_map.weeks`; dashboard wires upload success to timeline render |

All 5 requirement IDs from PLAN frontmatter accounted for. No orphaned requirements found (REQUIREMENTS.md maps AUTH-01/02/03/SYLL-01/02 to Phase 2, all claimed).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `template.yaml` | 30 | `# TODO: use SSM for prod` for JWT_SECRET | Info | Hardcoded dev secret is expected for local development; does not block phase goal |
| `frontend/components/AuthForm.tsx` | 38, 55 | `placeholder="..."` HTML attributes | Info | These are legitimate HTML input placeholder texts, not code stubs |

No blocker anti-patterns found. No stub implementations. No empty handlers. No unconnected state.

---

### Notable Deviation: HTTPBearer auto_error Behavior

The UAT plan (02-05) states unauthenticated requests return `403 {"detail": "Not authenticated"}` (FastAPI HTTPBearer default). The actual implementation uses `HTTPBearer(auto_error=False)` and manually raises `HTTPException(status_code=401)`. This is a deliberate and correct improvement — 401 is the semantically appropriate status code for missing credentials per RFC 7235. This does not constitute a gap; the phase goal is met, and the behavior is stricter than the plan's stated expectation.

---

### Human Verification Required

The UAT gate (Plan 02-05) was auto-approved without Docker running. The SUMMARY explicitly states: "UAT checkpoint auto-approved in auto-mode per `auto_advance: true` configuration — actual manual UAT verification should be performed when Docker Desktop is running."

All five live end-to-end tests below must be performed before Phase 2 can be considered fully closed:

#### 1. Registration

**Test:** Open http://localhost:3000 in browser. You should redirect to /login. Toggle to "Register" mode. Enter a username (3+ chars) and PIN (4-8 digits). Submit.
**Expected:** Redirected to /dashboard. Header shows "Hi, {username}". Token visible in localStorage via DevTools.
**Why human:** Requires live SAM backend with DynamoDB and a running Next.js dev server.

#### 2. Syllabus Upload and Timeline

**Test:** From /dashboard, click the upload area and select a real PDF syllabus file.
**Expected:** Upload succeeds, week/unit timeline appears below with course name and at least one week entry rendered.
**Why human:** Requires live Bedrock AI parsing, S3 write, and DynamoDB store. Cannot be verified statically.

#### 3. Logout and Re-Login

**Test:** Click "Sign out" on the dashboard. Confirm redirect to /login and localStorage cleared. Sign in again with the same username and PIN.
**Expected:** Redirected back to /dashboard. Token freshly issued and stored.
**Why human:** Tests the DynamoDB round-trip for credential verification after session is cleared.

#### 4. Cross-User Isolation (AUTH-02)

**Test:** Register a second user in an incognito window. Get the first user's `syllabus_id` from the browser Network tab. Run: `curl -H "Authorization: Bearer <user2_token>" http://127.0.0.1:3001/Prod/api/v1/syllabus/<user1_syllabus_id>`
**Expected:** `404 {"detail": "Syllabus not found."}`
**Why human:** Requires two live registered users and a real DynamoDB table with stored syllabus items.

#### 5. Unauthenticated Access Blocked

**Test:** `curl http://127.0.0.1:3001/Prod/api/v1/syllabus/anything` (no Authorization header)
**Expected:** `401 {"detail": "Not authenticated"}` (note: 401, not 403, due to `auto_error=False` implementation)
**Why human:** Requires live backend; also confirms the 401 vs 403 deviation is acceptable in practice.

---

## Summary

All 16 automated must-haves are verified. Every artifact exists, is substantively implemented (no stubs or placeholders), and all critical wiring is confirmed:

- Backend auth chain: `register_user` / `login_user` in `auth_service.py` → `store_user` / `get_user_by_username` in `dynamo_service.py` → `get_current_user` dependency in `middleware/auth.py` → wired into both syllabus routes via `Depends`
- Frontend auth chain: `AuthProvider` in root layout → `useAuth()` in login page → `apiFetch` + `decodeJwtPayload` → `setAuth` stores to localStorage → dashboard auth guard reads token
- Syllabus isolation: `store_syllabus` writes `user_id` to DynamoDB item; `get_syllabus` enforces ownership; cross-user returns `None` → 404

The only blocking item is the live UAT that was deferred due to Docker not running during auto-mode execution. The 5 human verification tests above must pass before Phase 2 can be signed off as complete.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
