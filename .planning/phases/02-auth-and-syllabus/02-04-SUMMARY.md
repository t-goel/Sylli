---
phase: 02-auth-and-syllabus
plan: "04"
subsystem: ui
tags: [nextjs, react, dashboard, auth-guard, file-upload, multipart, formdata]

# Dependency graph
requires:
  - phase: 02-auth-and-syllabus
    provides: AuthContext with token/username/logout, apiFetch helper, login page scaffold
provides:
  - dashboard/layout.tsx auth guard (redirects to /login if no token)
  - SyllabusUpload component (multipart FormData POST to /api/v1/syllabus with Authorization header)
  - WeekTimeline component (renders week_map.weeks[] defensively with nullish coalescing)
  - dashboard/page.tsx (composes upload + timeline with state management)
affects:
  - phase-03-materials
  - phase-04-chat

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Raw fetch with FormData for multipart uploads (not apiFetch which forces application/json)
    - Auth guard via Next.js layout.tsx useEffect + router.replace
    - Defensive rendering with nullish coalescing on all optional fields

key-files:
  created:
    - frontend/app/dashboard/layout.tsx
    - frontend/app/dashboard/page.tsx
    - frontend/components/SyllabusUpload.tsx
    - frontend/components/WeekTimeline.tsx
  modified: []

key-decisions:
  - "Raw fetch used in SyllabusUpload instead of apiFetch — apiFetch sets Content-Type: application/json which breaks multipart/form-data boundary"
  - "Auth guard implemented as layout.tsx, not middleware — uses AuthContext token state directly, consistent with client-side auth approach"

patterns-established:
  - "Multipart upload pattern: raw fetch + FormData, only inject Authorization header, let browser set Content-Type with boundary"
  - "Defensive component rendering: nullish coalescing on all optional fields (readings ?? [], notes, topic)"

requirements-completed:
  - SYLL-01
  - SYLL-02

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 2 Plan 04: Dashboard and Syllabus Upload UI Summary

**Next.js dashboard with auth guard layout, multipart PDF upload component, and defensive week timeline renderer delivering SYLL-01 and SYLL-02**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T19:58:15Z
- **Completed:** 2026-03-14T19:58:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Auth guard in dashboard/layout.tsx redirects unauthenticated users to /login via useEffect and router.replace
- SyllabusUpload.tsx submits PDF via raw fetch with FormData and Authorization Bearer header (correctly bypasses apiFetch's application/json Content-Type)
- WeekTimeline.tsx renders all week_map fields defensively — no crashes on missing notes, empty readings, or undefined fields
- Dashboard page composes all three with weekMap state set from upload response

## Task Commits

Each task was committed atomically:

1. **Task 1: Auth guard layout and WeekTimeline component** - `bd7a1e9` (feat)
2. **Task 2: Syllabus upload component and dashboard page** - `2b333ae` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `frontend/app/dashboard/layout.tsx` - Auth guard; redirects to /login if no token in AuthContext
- `frontend/components/WeekTimeline.tsx` - Renders week_map.weeks[] as vertical timeline with defensive nullish coalescing
- `frontend/components/SyllabusUpload.tsx` - File input that POSTs PDF via multipart FormData to /api/v1/syllabus
- `frontend/app/dashboard/page.tsx` - Dashboard page composing SyllabusUpload + WeekTimeline with weekMap state

## Decisions Made

- Used raw `fetch()` in SyllabusUpload rather than `apiFetch` — apiFetch always sets Content-Type: application/json which would override the browser-generated multipart/form-data boundary, breaking the upload
- Auth guard implemented as `layout.tsx` using `useAuth().token` in useEffect — consistent with the client-side auth context already established in plans 01-03

## Deviations from Plan

None — plan executed exactly as written. Build passed with zero TypeScript errors.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Dashboard with auth guard and syllabus upload is fully functional
- WeekTimeline renders whatever the backend returns, ready for integration
- Phase 3 (Materials) can now build on top of the established upload pattern

---
*Phase: 02-auth-and-syllabus*
*Completed: 2026-03-14*
