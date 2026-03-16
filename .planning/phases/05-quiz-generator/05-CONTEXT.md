# Phase 5: Quiz Generator - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Students can generate a multiple-choice quiz scoped to a selected unit/week or the full course, answer questions one at a time with immediate feedback and source-cited explanations. Creating quizzes, displaying them, and scoring them — that's the full scope. Adaptive difficulty, flashcards, and quiz history are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Quiz Flow
- Questions presented **one at a time** (step-through), not a scrollable form
- Header shows progress: "Question N of M"
- Navigation: Prev / Next buttons
- After the last question: results screen showing **score (X/N correct)** + ability to review each question with the correct answer highlighted
- Results screen has a **"New quiz"** button that returns to the scope/generate screen without leaving the tab

### Answer Feedback
- Feedback is **immediate** — as soon as the user selects an option, correct/incorrect is revealed and the explanation is shown
- Answers are **locked on selection** — no confirm button, no changing after selecting
- Explanation includes a **clickable citation link** in the same format as TutorChat: `filename — Week N: Topic Label` opens the source file in a new tab via presigned S3 URL
- Incorrect answers are visually marked (e.g. ✘); correct answer is highlighted (e.g. ✔)

### Scope & Size Controls
- Quiz tab shows a scope configuration screen before generating:
  - **Week dropdown**: "All weeks" + "Week N: Topic" entries (same data as TutorChat week filter, drawn from weekMap)
  - **Question count**: segmented control with options 5 / 10 / 15; **default is 5**
  - **Generate Quiz** button
- If the selected week has no embedded materials: **button is disabled** with an inline message ("No materials embedded for Week N")
- Generate button is disabled while generation is in progress (same pattern as TutorChat Send button)

### Generation UX
- While generating: centered **spinner + "Generating your quiz..."** message
- If generation fails (Bedrock error / timeout): **error message + Retry button** that re-submits the same scope
- Generate button is disabled during generation to prevent double-submission

### Claude's Discretion
- Exact question card styling (border, shadow, spacing)
- Score screen visual design (color for correct/incorrect counts)
- Exact system prompt wording for quiz generation
- How to handle the edge case where Bedrock returns fewer questions than requested
- Animation for the correct/incorrect reveal

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/embedding_service.py`: `embed_text()` + `_get_s3v()` — reuse for query embedding and S3 Vectors `query_vectors` call (same retrieval pattern as tutor)
- `backend/services/bedrock_service.py`: Bedrock Claude 3.5 Sonnet invocation — extend for quiz generation prompt
- `backend/middleware/auth.py` + `get_current_user`: Auth dependency already solved — quiz endpoint needs this
- `frontend/lib/api.ts`: `apiFetch` — use for quiz generation API call
- `frontend/app/dashboard/page.tsx`: Quiz tab already exists as placeholder (`disabled` on "quiz" tab) — just needs to be activated and wired to `<QuizTab />`
- `frontend/components/TutorChat.tsx`: Week dropdown pattern (`weekMap` prop, "All weeks" + per-week options) — replicate for quiz scope selector

### Established Patterns
- Services raise exceptions, routers catch as `HTTPException` — follow for quiz router
- `apiFetch` for all JSON API calls (auth header injected automatically)
- `user_id` partition key for all user-scoped data
- Lambda 30s timeout is a hard constraint — RAG retrieval + Bedrock quiz generation must complete within this window
- Citation click-to-open via presigned S3 URL — same pattern as library and tutor citations

### Integration Points
- `frontend/app/dashboard/page.tsx`: Remove `disabled` on quiz tab, render `<QuizTab weekMap={weekMap} />` when `activeTab === "quiz"`
- `backend/app.py`: Register new quiz router
- `template.yaml`: No new env vars needed — `VECTOR_BUCKET_NAME`, `VECTOR_INDEX_NAME`, `MATERIALS_TABLE` already set

</code_context>

<specifics>
## Specific Ideas

- The scope screen layout matches the mockup chosen: week dropdown on top, 5/10/15 segmented control below, Generate button at bottom
- Step-through question layout: question text, then four labeled options (A/B/C/D), then feedback expands below selected option after click
- Citation in explanation follows exact tutor format: `filename — Week N: Topic Label` as a clickable link

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-quiz-generator*
*Context gathered: 2026-03-16*
