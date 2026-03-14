---
phase: 02-auth-and-syllabus
plan: "03"
subsystem: ui
tags: [nextjs, react, typescript, tailwind, auth, jwt, localstorage]

# Dependency graph
requires:
  - phase: 02-auth-and-syllabus
    provides: "POST /api/v1/auth/register and POST /api/v1/auth/login endpoints returning { token }"
provides:
  - Next.js frontend scaffold with App Router, TypeScript, Tailwind CSS
  - AuthProvider and useAuth hook for global auth state via localStorage
  - apiFetch wrapper that injects Authorization Bearer header
  - decodeJwtPayload helper for client-side JWT payload extraction
  - Login/register page with username + PIN form and mode toggle
  - Root page redirect logic (/ -> /login or /dashboard based on token)
affects:
  - 02-04 (dashboard plan that builds on AuthContext and apiFetch)
  - All future frontend plans that use useAuth and apiFetch

# Tech tracking
tech-stack:
  added:
    - next@16.1.6 (App Router, TypeScript, Tailwind CSS)
    - react@19, react-dom@19
    - tailwindcss, @tailwindcss/postcss
  patterns:
    - AuthProvider wraps root layout for global auth state
    - localStorage as auth token store (token, user_id, username)
    - apiFetch wrapper pattern for all API calls with auto Bearer injection
    - Client-side JWT decode via atob (no library dependency)

key-files:
  created:
    - frontend/context/AuthContext.tsx
    - frontend/lib/api.ts
    - frontend/components/AuthForm.tsx
    - frontend/app/login/page.tsx
    - frontend/.env.local
  modified:
    - frontend/app/layout.tsx
    - frontend/app/page.tsx
    - .gitignore

key-decisions:
  - "Decode JWT client-side via atob on base64url payload segment — avoids adding jwt library dependency to frontend"
  - "API_BASE defaults to http://localhost:3001 (SAM local on 3001, avoids port 3000 conflict with Next.js)"
  - "localStorage for auth state — acceptable for PIN-based student app, no sensitive financial data"

patterns-established:
  - "apiFetch pattern: all API calls go through frontend/lib/api.ts which injects token from localStorage"
  - "AuthProvider pattern: root layout wraps children in AuthProvider, useAuth() hook accessible everywhere"
  - "Redirect pattern: root page.tsx checks token and redirects to /login or /dashboard"

requirements-completed: [AUTH-01, AUTH-03]

# Metrics
duration: 12min
completed: 2026-03-14
---

# Phase 2 Plan 03: Next.js Frontend Auth Scaffold Summary

**Next.js App Router frontend with AuthContext (localStorage token store), apiFetch wrapper with Bearer injection, and login/register page with client-side JWT decode via atob**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-14T19:51:28Z
- **Completed:** 2026-03-14T20:03:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Scaffolded complete Next.js 16 app with App Router, TypeScript, Tailwind CSS
- Implemented AuthContext with AuthProvider + useAuth hook backed by localStorage
- Built apiFetch wrapper and decodeJwtPayload (client-side base64url, no library)
- Created login/register page with two-field form, mode toggle, and /dashboard redirect on success
- Root page redirects to /login or /dashboard based on token presence
- Build verified: `npm run build` compiles clean with no TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold Next.js + AuthContext + API wrapper** - `5eb6b94` (feat)
2. **Task 2: Auth form component + login page + root redirect** - `ba08683` (feat)

## Files Created/Modified
- `frontend/context/AuthContext.tsx` - AuthProvider and useAuth hook with token/user_id/username
- `frontend/lib/api.ts` - apiFetch wrapper and decodeJwtPayload utility
- `frontend/components/AuthForm.tsx` - Username + PIN form with register/login mode toggle
- `frontend/app/login/page.tsx` - Login page: calls API, decodes JWT, calls setAuth, redirects
- `frontend/app/layout.tsx` - Root layout wrapping children in AuthProvider with dark theme
- `frontend/app/page.tsx` - Root redirect: token -> /dashboard, no token -> /login
- `frontend/.env.local` - NEXT_PUBLIC_API_URL=http://127.0.0.1:3001/Prod (gitignored)
- `.gitignore` - Added `!frontend/lib/` exception (root gitignore had `lib/` blocking ts files)

## Decisions Made
- Decode JWT client-side via `atob` on the base64url payload segment — avoids adding a jwt library dependency to the frontend, as specified in the plan's interfaces note.
- `API_BASE` defaults to `http://localhost:3001` because SAM local API Gateway runs on 3001 by default (port 3000 conflicts with Next.js dev server).
- localStorage for auth token storage — acceptable for a PIN-based student study app; no sensitive financial data.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed root .gitignore blocking frontend/lib/ directory**
- **Found during:** Task 1 (Scaffold Next.js + AuthContext + API wrapper)
- **Issue:** Root `.gitignore` contained `lib/` (a Python convention for virtualenvs), which matched `frontend/lib/` and prevented `git add frontend/lib/api.ts`
- **Fix:** Added `!frontend/lib/` negation rule to root `.gitignore` after the `lib/` entry
- **Files modified:** `.gitignore`
- **Verification:** `git add frontend/lib/api.ts` succeeded after fix
- **Committed in:** `5eb6b94` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** Fix was essential for committing the api.ts file. No scope creep.

## Issues Encountered
None beyond the gitignore deviation above.

## User Setup Required
None — `.env.local` is gitignored and pre-configured for SAM local. No external service configuration required.

## Next Phase Readiness
- Frontend auth scaffold complete; AuthContext and apiFetch available for Plan 04 (dashboard)
- Plan 04 can import `useAuth` and `apiFetch` directly
- Backend auth endpoints (Plans 01/02) must be running on port 3001 for end-to-end testing
- No blockers for Plan 04 execution

---
*Phase: 02-auth-and-syllabus*
*Completed: 2026-03-14*
