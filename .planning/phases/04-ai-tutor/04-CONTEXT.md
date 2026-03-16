# Phase 4: AI Tutor - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Students can ask questions about their course materials and receive answers grounded in their uploaded files, with source citations linking back to the specific material and week. Streaming, week-scoped-only mode, and saved chat history are v2 features. This phase delivers a functional synchronous RAG chat within the 30s Lambda constraint.

</domain>

<decisions>
## Implementation Decisions

### Chat UI Placement
- Three-tab layout on the dashboard: **Library | Tutor | Quiz**
- Quiz tab is a placeholder (Phase 5) — visible but disabled or shows "Coming soon"
- Default tab on dashboard load: **Library**
- Syllabus upload section behavior: once a syllabus is uploaded, the upload section is replaced by a compact "Replace syllabus" button that reveals the upload UI again on click

### Chat History
- Session-only — chat resets on page refresh (no DynamoDB persistence)
- The AI tutor receives the last **5 turns** of conversation history as context
- Loading state: animated typing indicator (dots) while waiting for AI response
- Send button is disabled while a request is in-flight

### Citation Display Style
- Each AI response ends with a separate **"Sources:" block** below the prose response
- Citation format per entry: `filename — Week N: Topic Label` (e.g., `lecture3.pdf — Week 3: Data Structures`)
- Citations are **clickable links** that open the source file directly in a new browser tab via presigned S3 URL (same behavior as library material clicks)

### Retrieval Scope Controls
- Chat header includes a **week filter dropdown** populated from the syllabus week_map
- Default selection: **"All weeks"** (unfiltered, searches all user materials)
- User can narrow to a specific week — S3 Vectors metadata already includes `week_number` for filtered queries
- RAG retrieval: **top 5 chunks** per query (balances context quality and Lambda 30s timeout)

### Tutor Persona
- Helpful study assistant — clear and concise
- Answers directly using course terminology from the materials
- Does not pad responses with filler; stays grounded in retrieved content

### Claude's Discretion
- Exact system prompt wording for the tutor persona
- How to handle the case where no relevant chunks are found (e.g., "I couldn't find relevant content in your materials for this question")
- Chat bubble styling (user vs. AI message visual distinction)
- Whether to use a `TutorChat.tsx` component or extend an existing component
- Error handling for failed Bedrock calls (display error in chat vs. toast)
- Exact animation style for typing indicator

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/embedding_service.py`: `embed_text()` + `_get_s3v()` — reuse for query embedding and S3 Vectors query_vectors call
- `backend/services/bedrock_service.py`: Bedrock claude 3.5 Sonnet invocation pattern — extend for chat completion with RAG context
- `backend/middleware/auth.py` + `get_current_user`: Auth dep already solved — all tutor endpoints need this
- `frontend/lib/api.ts`: `apiFetch` with auth header injection — use for chat API calls
- `frontend/components/MaterialLibrary.tsx`: Material data model and presigned URL fetching pattern — reuse for citation click-to-open

### Established Patterns
- Services raise exceptions, routers catch as HTTPException — follow for tutor router
- Raw `fetch` for file uploads; `apiFetch` for all JSON API calls
- `user_id` partition key for all user-scoped data
- Lambda 30s timeout is a hard constraint — RAG query + Bedrock call must complete within this window

### Integration Points
- `frontend/app/dashboard/page.tsx`: Add tab bar (Library | Tutor | Quiz) here; wrap existing content in Library tab
- `backend/app.py`: Register new tutor router
- `template.yaml`: Add tutor Lambda env vars if needed (VECTOR_BUCKET_NAME, VECTOR_INDEX_NAME already set for embedding)
- S3 Vectors `query_vectors` API: accepts `filter` dict with metadata conditions — use `{"user_id": user_id}` or `{"user_id": user_id, "week_number": N}` for scoped retrieval

</code_context>

<specifics>
## Specific Ideas

- The week filter dropdown options should mirror the week_map format: "All weeks" + "Week N: Topic" entries drawn from the syllabus
- The "Quiz" tab in Phase 4 is a placeholder — shows something like "Quiz generator coming soon" rather than being completely invisible
- Syllabus section collapses to a "Replace syllabus" button after upload (cleaner dashboard, less visual noise)
- Citation links use presigned S3 URLs generated on-click, same as library material opening

</specifics>

<deferred>
## Deferred Ideas

- Streaming chat responses (word-by-word) — TUTOR-V2-02 in REQUIREMENTS.md
- Week-scoped-only mode (restrict tutor to a single unit, no cross-week search) — TUTOR-V2-01
- Persistent chat history across sessions — v2

</deferred>

---

*Phase: 04-ai-tutor*
*Context gathered: 2026-03-16*
