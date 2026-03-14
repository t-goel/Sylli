# Requirements: Sylli AI

**Defined:** 2026-03-14
**Core Value:** Students can upload their course materials and study effectively through an AI that understands their course structure and timeline

## v1 Requirements

### Foundation

- [ ] **FOUND-01**: Bedrock JSON parse errors are caught and handled gracefully — no raw crashes exposed to the client
- [ ] **FOUND-02**: Bedrock invocations have timeout and retry handling — no silent Lambda kills on real documents
- [ ] **FOUND-03**: SAM template and Lambda function are renamed from HelloWorld to Sylli project naming

### Auth

- [ ] **AUTH-01**: User can create a session by entering a username and PIN
- [ ] **AUTH-02**: User's data (syllabus, materials, chat history) is scoped to their username
- [ ] **AUTH-03**: User can log out and return with the same username + PIN to access their data

### Syllabus

- [ ] **SYLL-01**: User can upload a course syllabus PDF through the UI to initialize their course
- [ ] **SYLL-02**: User can view the parsed week/unit timeline after syllabus upload

### Materials

- [ ] **MAT-01**: User can upload PDF or PPTX files as course materials
- [ ] **MAT-02**: AI suggests which unit/week an uploaded material belongs to (based on parsed syllabus)
- [ ] **MAT-03**: User can confirm or override the AI-suggested unit/week assignment for each material
- [ ] **MAT-04**: Uploaded materials are chunked and embedded asynchronously (non-blocking upload flow)
- [ ] **MAT-05**: Embeddings are stored with user_id and unit/week metadata for filtered retrieval

### Library Navigator

- [ ] **LIB-01**: User can view all uploaded materials organized by unit/week in a chronological timeline
- [ ] **LIB-02**: User can click a material in the library to view the original file

### AI Tutor

- [ ] **TUTOR-01**: User can chat with an AI tutor that answers questions using their uploaded course materials
- [ ] **TUTOR-02**: Every AI tutor response cites the specific source file and unit/week it referenced

### Quiz Generator

- [ ] **QUIZ-01**: User can generate a multiple-choice quiz scoped to a selected unit/week
- [ ] **QUIZ-02**: User can generate a multiple-choice quiz spanning all uploaded course materials
- [ ] **QUIZ-03**: Each quiz answer includes an explanation citing the source material it was drawn from

## v2 Requirements

### Auth

- **AUTH-V2-01**: Password reset via email
- **AUTH-V2-02**: Full Cognito-based auth if app goes to production

### Library

- **LIB-V2-01**: Manual week/unit assignment override in library view
- **LIB-V2-02**: Material delete from course
- **LIB-V2-03**: Current week highlighted/indicated in timeline

### AI Tutor

- **TUTOR-V2-01**: Week-scoped mode — restrict tutor to a single unit's materials
- **TUTOR-V2-02**: Streaming chat responses (word-by-word output)

### Courses

- **COURSE-V2-01**: User can manage multiple courses simultaneously

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full Cognito / production auth | App won't go to prod; username+PIN is sufficient |
| Spaced repetition / adaptive difficulty | Doubles scope without validating core premise |
| Flashcards | Separate product; not in three-pillar design |
| Audio/video content | Complex extraction pipeline; defer |
| Mobile app | Web-first |
| Bedrock Knowledge Bases | No per-user data isolation — unsafe for multi-user |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| SYLL-01 | Phase 2 | Pending |
| SYLL-02 | Phase 2 | Pending |
| MAT-01 | Phase 3 | Pending |
| MAT-02 | Phase 3 | Pending |
| MAT-03 | Phase 3 | Pending |
| MAT-04 | Phase 3 | Pending |
| MAT-05 | Phase 3 | Pending |
| LIB-01 | Phase 3 | Pending |
| LIB-02 | Phase 3 | Pending |
| TUTOR-01 | Phase 4 | Pending |
| TUTOR-02 | Phase 4 | Pending |
| QUIZ-01 | Phase 5 | Pending |
| QUIZ-02 | Phase 5 | Pending |
| QUIZ-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after initial definition*
