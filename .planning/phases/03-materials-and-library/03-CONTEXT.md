# Phase 3: Materials and Library - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Students can upload PDF and PPTX course materials, confirm the AI-suggested unit/week assignment, and browse all materials in a chronological library organized by week. Async embedding runs in the background after confirmation. AI Tutor (Phase 4) consumes the embeddings — that's out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Unit Assignment Flow
- Inline confirmation: after upload completes, the upload row expands showing the AI-suggested week with [✓ Confirm] and [✎ Change week] buttons
- "Change week" opens a dropdown populated from the parsed week_map (e.g., "Week 3: Data Structures")
- Unconfirmed materials appear in the library immediately under the AI-suggested week with a subtle "Unconfirmed" badge
- Materials are NOT hidden until confirmation — non-blocking flow
- Upload entry point is on the existing dashboard page (extend below the syllabus upload section, above the library)

### Library Layout
- Sections per week, always expanded — no collapse/accordion
- All weeks from the syllabus are shown, including empty ones ("no materials yet")
- Each material row shows: file type icon (PDF/PPTX) + filename
- Unconfirmed materials show a subtle "Unconfirmed" badge in the library row

### File Viewing
- Clicking a material opens it directly in a new browser tab via a presigned S3 URL
- URL is generated on-demand each click (no caching) — most secure, same latency as a fetch
- No intermediate details panel — click = open

### Embedding Status Feedback
- Each material shows a "Processing..." badge that transitions to a checkmark when embedding completes
- Frontend polls the material status endpoint every ~4 seconds until status = 'ready', then clears the interval
- Embedding does NOT start on upload — it triggers after the user confirms the week assignment
- This ensures embeddings are stored with final (user-confirmed) week metadata for filtered retrieval

### Claude's Discretion
- Exact polling interval (3-5s range acceptable)
- Specific CSS/styling for the Unconfirmed badge and Processing indicator
- Whether to create a new `MaterialUpload` component or extend `SyllabusUpload`
- DynamoDB schema for materials table (key structure, attribute names)
- Vector store selection (S3 Vectors vs OpenSearch Serverless — must be AWS-only per project constraint)
- Lambda async invocation pattern for embedding (SNS, SQS, or async Lambda invoke)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/components/SyllabusUpload.tsx`: Upload pattern (multipart/form-data with raw fetch to avoid Content-Type conflict) — mirror this for material upload
- `frontend/components/WeekTimeline.tsx`: Renders week/unit sections from week_map — extend or compose for the library view
- `frontend/lib/api.ts`: `apiFetch` with auth header injection — use for all material API calls
- `backend/routers/syllabus.py`: Router pattern (upload + fetch) — mirror for materials router
- `backend/middleware/auth.py` + `get_current_user`: Auth dep already solved — reuse on all material endpoints
- `backend/services/dynamo_service.py`: DynamoDB pattern — extend for materials table operations
- `backend/services/syllabus_service.py`: S3 upload pattern — reuse for material file storage

### Established Patterns
- Raw `fetch` (not `apiFetch`) for file uploads — apiFetch sets Content-Type: application/json which breaks multipart/form-data
- Services raise exceptions naturally; routers catch and return HTTPException
- `user_id` is the partition key for user data scoping (UUID from JWT)
- `localStorage.getItem("syllabus_id")` pattern — mirror `material_id` storage if needed

### Integration Points
- Dashboard page (`frontend/app/dashboard/page.tsx`): Add MaterialUpload section and library view here
- `backend/app.py`: Register new materials router
- `template.yaml`: May need new environment variables (vector store endpoint/config) and IAM permissions (Bedrock embeddings, new DynamoDB table)
- The syllabus `week_map` (fetched on dashboard load) feeds the week dropdown for assignment confirmation

</code_context>

<specifics>
## Specific Ideas

- The assignment confirmation UI should feel inline and immediate — not a modal, not a separate page
- The library should extend the existing weekly timeline aesthetic already established by WeekTimeline
- Presigned URL is generated fresh each click for security (no URL caching)
- Embedding only starts after user confirms week — ensures week metadata in the vector store is always the user's final intent

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-materials-and-library*
*Context gathered: 2026-03-14*
