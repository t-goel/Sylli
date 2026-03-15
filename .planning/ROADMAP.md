# Roadmap: Sylli AI

## Overview

Sylli is a brownfield project with a working syllabus-parsing backend. The work ahead is five sequential phases: stabilize the existing foundation, add auth and a frontend, build the material upload pipeline with a library view, implement the RAG-powered AI tutor, and finally add the quiz generator on top of validated retrieval quality. Each phase delivers one verifiable capability that the next phase depends on. The `week_map` structure already on the backend is the key differentiator — everything is built to express and leverage it.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Fix existing bugs and stabilize the backend before any new features land (completed 2026-03-14)
- [x] **Phase 2: Auth and Syllabus** - Gate data behind user accounts and deliver the first UI milestone (completed 2026-03-14)
- [x] **Phase 3: Materials and Library** - Upload course materials with async embedding and display a chronological navigator (completed 2026-03-15)
- [ ] **Phase 4: AI Tutor** - RAG pipeline with week-aware context and inline source citations
- [ ] **Phase 5: Quiz Generator** - On-demand quiz generation scoped to a unit or the full course

## Phase Details

### Phase 1: Foundation
**Goal**: The existing backend is stable, named correctly, and will not crash or silently time out on real course materials
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03
**Success Criteria** (what must be TRUE):
  1. Uploading a real multi-page syllabus PDF does not return a 500 or expose raw error text — Bedrock JSON parse errors are caught and a clean error message is returned
  2. A large syllabus PDF that would previously cause a Lambda timeout completes without a silent kill — timeout and retry handling is in place on all Bedrock invocations
  3. The Lambda function, SAM template, and all project references are named `Sylli` (no remaining `HelloWorld` identifiers)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Bedrock error handling and timeout/retry (FOUND-01, FOUND-02)
- [ ] 01-02-PLAN.md — HelloWorld purge: rename template.yaml, update SPEC.md, delete dead files (FOUND-03)

### Phase 2: Auth and Syllabus
**Goal**: Each student has a private account, and after logging in they can upload their course syllabus and see the parsed timeline
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, SYLL-01, SYLL-02
**Success Criteria** (what must be TRUE):
  1. A user can register with a username and PIN and immediately access the app
  2. A user's syllabus, materials, and chat history are not visible to any other user
  3. A user can log out and log back in with the same username and PIN to reach their data
  4. A logged-in user can upload a course syllabus PDF through the Next.js UI
  5. After upload, the user can see their course's week/unit timeline displayed from the parsed week_map
**Plans**: 5 plans

Plans:
- [ ] 02-01-PLAN.md — Backend auth foundation: users table, PyJWT + passlib, auth service, JWT middleware (AUTH-01, AUTH-02, AUTH-03)
- [ ] 02-02-PLAN.md — Auth API endpoints + syllabus user_id enforcement + CORS (AUTH-01, AUTH-02, AUTH-03, SYLL-01)
- [ ] 02-03-PLAN.md — Next.js scaffold + AuthContext + login/register page (AUTH-01, AUTH-03)
- [ ] 02-04-PLAN.md — Dashboard + syllabus upload component + week timeline (SYLL-01, SYLL-02)
- [ ] 02-05-PLAN.md — UAT checkpoint: verify all 5 Phase 2 success criteria (AUTH-01, AUTH-02, AUTH-03, SYLL-01, SYLL-02)

### Phase 3: Materials and Library
**Goal**: Students can upload lecture slides and notes, have them assigned to a week automatically, and browse everything in a chronological course view
**Depends on**: Phase 2
**Requirements**: MAT-01, MAT-02, MAT-03, MAT-04, MAT-05, LIB-01, LIB-02
**Success Criteria** (what must be TRUE):
  1. A user can upload a PDF or PPTX file and the upload returns immediately without waiting for embedding to complete
  2. After upload, the AI suggests which unit/week the material belongs to — the user can confirm or change the assignment before saving
  3. Uploaded materials appear organized by unit/week in a chronological library view
  4. The user can click any material in the library to view the original file
  5. Embeddings for uploaded materials are stored with user_id and unit/week metadata so they can be filtered during retrieval
**Plans**: 5 plans

Plans:
- [ ] 03-01-PLAN.md — Infrastructure: requirements.txt deps, SAM resources (MaterialsBucket, MaterialsTable w/ GSI, EmbedWorkerFunction, IAM policies) (MAT-01, MAT-04, MAT-05)
- [ ] 03-02-PLAN.md — Backend material router: 5 endpoints, material_service, dynamo extensions, AI week suggestion, async Lambda trigger (MAT-01, MAT-02, MAT-03, LIB-01, LIB-02)
- [ ] 03-03-PLAN.md — Async embedding pipeline: embedding_service, embed worker Lambda, text extraction, S3 Vectors write (MAT-04, MAT-05)
- [ ] 03-04-PLAN.md — Frontend: MaterialUpload (inline confirmation + polling), MaterialLibrary (week-organized), dashboard wiring (MAT-01, MAT-02, MAT-03, MAT-04, LIB-01, LIB-02)
- [ ] 03-05-PLAN.md — UAT checkpoint: verify all 5 Phase 3 success criteria (MAT-01, MAT-02, MAT-03, MAT-04, MAT-05, LIB-01, LIB-02)

### Phase 4: AI Tutor
**Goal**: Students can ask questions about their course and receive answers grounded in their uploaded materials with citations back to the source
**Depends on**: Phase 3
**Requirements**: TUTOR-01, TUTOR-02
**Success Criteria** (what must be TRUE):
  1. A user can type a question in the chat UI and receive an answer drawn from their own uploaded course materials (not generic LLM knowledge)
  2. Every AI tutor response includes at least one citation naming the specific source file and unit/week it referenced
**Plans**: TBD

### Phase 5: Quiz Generator
**Goal**: Students can generate a multiple-choice quiz scoped to any unit or the full course and see explanations tied back to source material
**Depends on**: Phase 4
**Requirements**: QUIZ-01, QUIZ-02, QUIZ-03
**Success Criteria** (what must be TRUE):
  1. A user can select a unit/week and generate a multiple-choice quiz scoped to only that unit's materials
  2. A user can generate a quiz spanning all uploaded course materials
  3. After answering each question, the user sees an explanation that cites the source material the answer was drawn from
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete   | 2026-03-14 |
| 2. Auth and Syllabus | 5/5 | Complete | 2026-03-14 |
| 3. Materials and Library | 5/5 | Complete   | 2026-03-15 |
| 4. AI Tutor | 0/TBD | Not started | - |
| 5. Quiz Generator | 0/TBD | Not started | - |
