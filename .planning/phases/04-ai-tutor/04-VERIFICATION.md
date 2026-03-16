---
phase: 04-ai-tutor
verified: 2026-03-16T23:00:00Z
status: human_needed
score: 20/20 automated checks verified
re_verification:
  previous_status: human_needed
  previous_score: 17/17
  gaps_closed:
    - "Delete button fix: res.ok check stops silent error swallowing (commit 4b80ae4)"
    - "deletingId guard prevents double-click / concurrent deletes"
    - "await onRefresh() ensures list refreshes only after DELETE commits server-side"
    - "deleteError state surfaces API error message to user as inline red banner"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Submit a question in the Tutor tab and receive an AI answer grounded in uploaded materials"
    expected: "Answer references content from uploaded course materials, not generic LLM knowledge"
    why_human: "Requires live stack (sam local start-api + npm run dev) with real DynamoDB data and embedded vectors in S3 Vectors"
  - test: "Verify Sources block appears with at least one clickable citation after receiving an AI answer"
    expected: "Citation displays as 'filename — Week N: Topic Label'; clicking opens the original file in a new tab"
    why_human: "Requires live presigned S3 URL generation and browser interaction to confirm link opens correctly"
  - test: "Select a specific week in the dropdown filter, then ask a question"
    expected: "Answer references only materials from that week (or returns the no-content guard message if no embedded materials exist for that week)"
    why_human: "Requires live vector retrieval with real week_number metadata to confirm filter scoping works"
  - test: "Select a week with no embedded materials and ask any question"
    expected: "Receive 'I couldn't find relevant content in your materials...' message, not a generic LLM answer"
    why_human: "Requires a known empty-week slot in the user's data to confirm short-circuit path triggers"
  - test: "Observe the Send button and typing indicator during a request"
    expected: "Send button is disabled and three animated dots appear while waiting for response; button re-enables on completion"
    why_human: "Loading state and animation are visual behaviors that cannot be verified by static code analysis"
  - test: "Confirm syllabus section collapse behavior after syllabus is loaded"
    expected: "Compact 'Replace syllabus' button visible instead of full upload UI; clicking it expands the upload form"
    why_human: "Conditional render based on weekMap state requires live browser session to confirm"
  - test: "Upload a material, confirm its week, and simulate a Lambda invocation failure"
    expected: "Material row shows red 'Embedding failed' badge (not infinite 'Processing...'); DynamoDB embed_status is 'error'"
    why_human: "Requires a deployed environment where EMBED_FUNCTION_NAME is set to a nonexistent function to trigger the error path"
  - test: "Delete a material with embed_status='error' from the library"
    expected: "Row disappears from the list after the DELETE request commits; delete button shows '...' then vanishes; no double-fire on rapid clicking"
    why_human: "Requires live server with an actual failed material row; button disabled state and list update require browser interaction"
  - test: "Trigger a DELETE API failure (e.g., delete an already-deleted material) and observe the UI"
    expected: "Row stays in the list; a red error message appears above the week list; subsequent clicks still work"
    why_human: "Requires a live server to return a 404 or 500 on the DELETE endpoint and confirm error banner renders"
---

# Phase 4: AI Tutor Verification Report

**Phase Goal:** Students can ask questions about their course and receive answers grounded in their uploaded materials with citations back to the source
**Verified:** 2026-03-16T23:00:00Z
**Status:** human_needed (all automated checks pass)
**Re-verification:** Yes — after gap closure plans 04-04 and 04-05

## Gap Closure Summary

Plan 04-04 (commit `44c7b85`) fixed a silent `except: pass` in `confirm_material_week()` that swallowed Lambda invocation errors, leaving `embed_status` stuck at `'pending'` forever.

Plan 04-05 (commit `4b80ae4`) fixed three bugs in `handleDeleteMaterial` in `MaterialLibrary.tsx`: API errors were silently swallowed (no `res.ok` check), `onRefresh()` was called without `await` causing a race condition, and there was no loading guard against double-clicks.

All 20 automated truths are now VERIFIED. No regressions detected on previously-passing truths.

---

## Goal Achievement

### Observable Truths (Plans 01–03 — Core RAG Pipeline)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/v1/tutor/chat returns 200 with answer and citations list when relevant materials exist | VERIFIED | `router.post("/chat", response_model=ChatResponse)` in `routers/tutor.py`; full RAG pipeline in `ask()` |
| 2 | Retrieval is scoped to user_id — a user never sees chunks from another user's materials | VERIFIED | `filter_expr = {"user_id": {"$eq": user_id}}` always present in `retrieve_chunks()` |
| 3 | When week_number is provided, only chunks from that week are retrieved | VERIFIED | `$and` filter with `{"week_number": {"$eq": week_number}}` in `retrieve_chunks()` |
| 4 | When zero chunks are retrieved, the endpoint returns a clear no-content message without calling Bedrock | VERIFIED | `if not chunks: return {"answer": "I couldn't find relevant content...", "citations": []}` short-circuits before `generate_answer()` |
| 5 | Every citation includes filename, week_number, and a presigned S3 URL | VERIFIED | `build_citations()` calls `get_material()` for filename and `get_presigned_url()` for URL; `Citation` Pydantic model has all three fields |
| 6 | Dashboard shows a three-tab bar: Library (default), Tutor, Quiz (disabled/coming soon) | VERIFIED | `activeTab` state initialized to `"library"`; map over `["library","tutor","quiz"]`; quiz tab has `disabled` prop |
| 7 | Switching to Tutor tab shows the TutorChat component | VERIFIED | `{activeTab === "tutor" && <TutorChat weekMap={weekMap} />}` in `page.tsx` |
| 8 | Once a syllabus is uploaded, the syllabus section collapses to a compact Replace Syllabus button | VERIFIED | `weekMap === null` conditional: null shows full `<SyllabusUpload>`, non-null shows Replace button |
| 9 | User can type a question and click Send to receive an AI answer in the chat UI | VERIFIED | `handleSend()` calls `apiFetch("/api/v1/tutor/chat", ...)` and appends assistant message on success |
| 10 | Send button is disabled while a request is in-flight; animated typing indicator shows while waiting | VERIFIED | `disabled={loading \|\| input.trim() === ""}` on button; `{loading && <TypingIndicator />}` with `animate-bounce` spans |
| 11 | AI response ends with a Sources block listing citations in filename — Week N: Topic format | VERIFIED | Citations block rendered when `citations.length > 0`; label built as `Week ${c.week_number}: ${weekEntry.topic}` |
| 12 | Each citation in Sources block is a clickable link that opens the file in a new tab | VERIFIED | `<a href={c.url} target="_blank" rel="noopener noreferrer">` conditional on `c.url` being truthy |
| 13 | Chat history resets on page refresh (session-only state) | VERIFIED | `const [messages, setMessages] = useState<ChatMessage[]>([])` — no persistence |

### Observable Truths (Plan 04 — Gap Closure: Lambda Error Propagation)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 14 | When Lambda invocation fails, embed_status is set to 'error' in DynamoDB (not left at 'pending') | VERIFIED | `update_material_embed_status(material_id, "error")` called in `except Exception as exc:` block in `material_service.py` |
| 15 | The exception is logged so it appears in CloudWatch (not silently swallowed) | VERIFIED | `logger.exception("Lambda invoke failed for material %s: %s", material_id, exc)` present; `import logging` and `logger = logging.getLogger(__name__)` at top of file |
| 16 | The API confirm response returns embed_status='error' immediately on invocation failure | VERIFIED | `return {"material_id": material_id, "embed_status": "error"}` inside except block — early return before happy-path fallthrough |
| 17 | The frontend poll terminates when it receives embed_status='error' and shows 'Embedding failed' | VERIFIED | `if status === "ready" \|\| status === "error": clearInterval(...)` in `MaterialUpload.tsx`; `{embedStatus === "error" && <p ...>Embedding failed</p>}` rendered |

### Observable Truths (Plan 05 — Gap Closure: Delete Button Fix)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 18 | A material that failed to upload can be deleted from the library | VERIFIED | `handleDeleteMaterial` is now inline in component; calls `apiFetch(.../materials/${materialId}, { method: "DELETE" })`; `res.ok` check present; `await onRefresh()` updates list after commit — commit `4b80ae4` |
| 19 | Clicking delete once removes the item and refreshes the list exactly once | VERIFIED | `if (deletingId !== null) return` guard at top of handler prevents concurrent invocations; `await onRefresh()` called exactly once in the `try` block after `res.ok` check |
| 20 | If the DELETE API call fails, the item stays in the list and the user sees an error | VERIFIED | `if (!res.ok) { setDeleteError(body.detail ?? "Delete failed — please try again"); return }` — early return before `onRefresh()`; `{deleteError && <p ...>{deleteError}</p>}` renders error banner above list |

**Score:** 20/20 automated truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/services/material_service.py` | `confirm_material_week` with proper exception propagation | VERIFIED | `import logging`, `logger = logging.getLogger(__name__)`, `except Exception as exc:` with `logger.exception`, `update_material_embed_status(material_id, "error")`, early return — all present |
| `backend/services/tutor_service.py` | RAG orchestration: embed query -> query_vectors -> generate answer -> build citations | VERIFIED | Exports `ask()`, `retrieve_chunks()`, `build_citations()`, `generate_answer()` — all fully implemented |
| `backend/routers/tutor.py` | POST /tutor/chat endpoint | VERIFIED | `APIRouter(prefix="/tutor")`; `@router.post("/chat")`; Pydantic models `ChatRequest`, `ChatResponse`, `Citation` all present |
| `backend/app.py` | tutor router registered at /api/v1 | VERIFIED | `from routers import health, syllabus, auth, materials, tutor`; `app.include_router(tutor.router, prefix="/api/v1")` |
| `template.yaml` | s3vectors:QueryVectors + s3vectors:GetVectors IAM permissions on SylliFunction | VERIFIED | Both permissions found; `VECTOR_BUCKET_NAME`, `VECTOR_INDEX_NAME`, `AWS_REGION_NAME` in SylliFunction env vars |
| `frontend/components/TutorChat.tsx` | Chat UI with session state, week filter dropdown, message list, citation links | VERIFIED | 205 lines; all required UI elements present and wired |
| `frontend/app/dashboard/page.tsx` | Three-tab layout wrapping Library/Tutor/Quiz; collapsed syllabus section | VERIFIED | `activeTab` state; three-tab render; syllabus collapse conditional; `onRefresh={fetchMaterials}` passed to `MaterialLibrary` |
| `frontend/components/MaterialUpload.tsx` | Poll termination on embed_status='error'; 'Embedding failed' badge | VERIFIED | `status === "ready" \|\| status === "error"` stops polling; "Embedding failed" rendered in red |
| `frontend/components/MaterialLibrary.tsx` | Fixed handleDeleteMaterial with res.ok check, awaited refresh, and loading guard | VERIFIED | 142 lines; `useState` import, `deletingId`/`deleteError` state, inline `handleDeleteMaterial`, `res.ok` check, `await onRefresh()`, disabled button during in-flight, error banner — all present; `4b80ae4` confirmed via `git show` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/routers/tutor.py` | `backend/services/tutor_service.py` | `ask()` call | WIRED | `from services import tutor_service`; `tutor_service.ask(...)` called in chat endpoint |
| `backend/services/tutor_service.py` | `embedding_service.embed_text` | query embedding | WIRED | `embed_text(question)` called in `ask()` |
| `backend/services/tutor_service.py` | `s3vectors.query_vectors` | similarity search | WIRED | `s3v.query_vectors(vectorBucketName=VECTOR_BUCKET_NAME, ...)` in `retrieve_chunks()` |
| `backend/services/tutor_service.py` | `bedrock_service.bedrock.converse` | answer generation | WIRED | `bedrock.converse(modelId=MODEL_ID, ...)` in `generate_answer()` |
| `backend/services/tutor_service.py` | `material_service.get_presigned_url` | citation URL generation | WIRED | `get_presigned_url(mid, user_id)` in `build_citations()` |
| `frontend/components/TutorChat.tsx` | `/api/v1/tutor/chat` | apiFetch POST | WIRED | `apiFetch("/api/v1/tutor/chat", { method: "POST", body: JSON.stringify({...}) })` in `handleSend()` |
| `frontend/app/dashboard/page.tsx` | `TutorChat` | import and render in tutor tab | WIRED | `import { TutorChat } from "@/components/TutorChat"`; `<TutorChat weekMap={weekMap} />` when `activeTab === "tutor"` |
| `frontend/components/TutorChat.tsx` | `citation.url` (presigned S3 URL) | anchor tag target=_blank | WIRED | `<a href={c.url} target="_blank" rel="noopener noreferrer">` conditional on `c.url` truthy |
| `backend/services/material_service.py` | `dynamo_service.update_material_embed_status` | error path | WIRED | `update_material_embed_status(material_id, "error")` called in `except` block; import present |
| `frontend/components/MaterialUpload.tsx` | poll stop on error | `clearInterval` when status='error' | WIRED | `if (status === "ready" \|\| status === "error") { clearInterval(intervalRef.current!) }` |
| `frontend/components/MaterialLibrary.tsx` delete button | `handleDeleteMaterial` | onClick + deletingId guard | WIRED | `onClick={() => handleDeleteMaterial(material.material_id)}`; `disabled={deletingId === material.material_id}`; guard `if (deletingId !== null) return` at top of handler |
| `handleDeleteMaterial` | `onRefresh()` | await after res.ok check | WIRED | `await onRefresh()` called only inside `if (res.ok)` path; `fetchMaterials` (async) passed as `onRefresh` from `page.tsx` line 153 |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| TUTOR-01 | 04-01, 04-02, 04-03, 04-04 | User can chat with an AI tutor that answers questions using their uploaded course materials | SATISFIED | Backend RAG endpoint (`tutor_service.ask()`) + frontend `TutorChat` fully wired; Lambda error propagation fix ensures embedding failures surface rather than silently blocking RAG |
| TUTOR-02 | 04-01, 04-02, 04-03 | Every AI tutor response cites the specific source file and unit/week it referenced | SATISFIED | `build_citations()` assembles `{filename, week_number, url}` per unique material; frontend renders `filename — Week N: Topic` with clickable presigned S3 URL anchors |
| LIB-02 | 04-05 | User can click a material in the library to view the original file | NOTE — see below | Plan 04-05 claims LIB-02 but implements a delete fix, not view-file behavior. LIB-02 (view) was satisfied in Phase 3 via `handleOpenMaterial`. The delete capability is LIB-V2-02 in REQUIREMENTS.md. No gap in implementation — this is a labeling mismatch in the plan frontmatter only. |

**Requirement label note:** Plan 04-05 tagged `LIB-02` in its frontmatter, but LIB-02 is described as "User can click a material in the library to view the original file" and is already marked Complete in Phase 3. The delete fix implemented in 04-05 maps to `LIB-V2-02` ("Material delete from course"). REQUIREMENTS.md traceability table does not list LIB-V2-02 as Phase 4, so this is an orphan label in the plan only — no functional gap. The delete behavior is fully implemented and the view behavior (true LIB-02) was confirmed in Phase 3.

**Orphaned requirement check:** REQUIREMENTS.md maps only TUTOR-01 and TUTOR-02 to Phase 4. LIB-02 is mapped to Phase 3 (complete). No requirement IDs are assigned to Phase 4 in REQUIREMENTS.md that are unclaimed by phase plans.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/services/material_service.py` | ~122 | `except Exception: pass` in `delete_material` | Info | Intentional — S3 object may already be gone on delete; not a bug. Confirmed unchanged per plan 04-04 spec. |
| `frontend/components/TutorChat.tsx` | 191 | `placeholder=` attribute on input | Info | HTML input placeholder text, not a code stub — no impact |
| `frontend/components/MaterialLibrary.tsx` | 28 | `onRefresh: () => void` prop type while `await onRefresh()` is used | Info | TypeScript compiles clean (`npx tsc --noEmit` exits 0). `await` on a `void`-returning function is a no-op in terms of TypeScript type checking. At runtime, `fetchMaterials` is `async function` so the await is meaningful. Functionally correct. |

No blocker or warning-level anti-patterns. No `TODO`, `FIXME`, or unimplemented stubs detected.

---

### Human Verification Required

All 20 automated checks pass. The following items require a live running stack:

#### 1. AI Answer Quality (TUTOR-01 core)

**Test:** Log in, navigate to Tutor tab, type a question about one of your uploaded course materials (e.g., "What is covered in Week 2?"), and submit.
**Expected:** AI answer references specific content from uploaded materials, not generic LLM knowledge; animated three-dot typing indicator appears while waiting.
**Why human:** Requires live `sam local start-api` + `npm run dev` with real DynamoDB entries and embedded vectors in S3 Vectors.

#### 2. Citation Links (TUTOR-02 core)

**Test:** After receiving an AI answer, inspect the Sources block.
**Expected:** At least one citation displayed as `filename — Week N: Topic Label`; clicking the link opens the original file in a new browser tab via presigned S3 URL.
**Why human:** Presigned URL generation requires live AWS credentials and an actual S3 object; link behavior requires browser interaction.

#### 3. Week Filter Scoping

**Test:** Select a specific week from the header dropdown, ask a question relevant to that week.
**Expected:** Answer draws only from that week's materials (or returns no-content guard if no embeddings exist for that week).
**Why human:** Filter correctness depends on actual `week_number` metadata stored in S3 Vectors from the Phase 3 embedding pipeline.

#### 4. No-Content Guard Path

**Test:** Select a week that has no embedded materials, ask any question.
**Expected:** Receive the message "I couldn't find relevant content in your materials for this question. Make sure your materials have finished processing (check the Library tab)."
**Why human:** Requires a known empty-week configuration in the test dataset; confirming Bedrock is not called requires observing Lambda logs.

#### 5. Send Button Loading State

**Test:** Submit a question and observe the Send button and input field during the pending request.
**Expected:** Send button becomes disabled (grey) and typing indicator (three bouncing dots) is visible; both reset to normal state after response arrives.
**Why human:** Loading state and CSS animation are visual behaviors; `disabled` and `animate-bounce` attributes verified statically but rendering requires browser.

#### 6. Syllabus Collapse Interaction

**Test:** Load dashboard with an existing syllabus; observe the syllabus section.
**Expected:** Only a small "Replace syllabus" text button is visible (no full upload UI); clicking it expands the upload form; clicking "Cancel" collapses it again.
**Why human:** Conditional render depends on `weekMap` state being populated from the API call, which requires a live server.

#### 7. Lambda Error Path — 'Embedding Failed' Badge (Plan 04-04 gap closure)

**Test:** Deploy with `EMBED_FUNCTION_NAME` pointing to a nonexistent Lambda function name, upload a material, and confirm its week assignment.
**Expected:** Material row shows a red "Embedding failed" badge within one poll cycle (4 seconds); the row does not show "Processing..." indefinitely; DynamoDB `embed_status` field is `'error'`.
**Why human:** Requires a deployed environment with AWS credentials and an intentionally broken `EMBED_FUNCTION_NAME` to trigger the error path.

#### 8. Delete Flow — Success Path (Plan 04-05 gap closure)

**Test:** Navigate to the Library tab with at least one material (ideally one with `embed_status='error'`). Hover over the row to reveal the delete button (✕). Click it once.
**Expected:** Button shows "..." immediately, row disappears from the list after a moment, no error banner appears.
**Why human:** Requires a live server with a real material row and real DELETE endpoint; button hover state and row disappearance are visual behaviors requiring browser interaction.

#### 9. Delete Flow — Error Path (Plan 04-05 gap closure)

**Test:** Attempt to delete a material that has already been deleted (or cause the DELETE to return a non-2xx by other means).
**Expected:** Row stays in the list; a small red error message appears above the week list; the delete button re-enables and can be clicked again.
**Why human:** Requires a live server configured to return an error on DELETE; error banner rendering requires browser confirmation.

---

### Gaps Summary

No gaps remain. All 20 automated checks passed at all three verification levels (exists, substantive, wired). This includes the 3 new truths from plan 04-05 gap closure (delete fix), the 4 truths from plan 04-04 gap closure (Lambda error propagation), and all 13 original truths from plans 01–03.

TypeScript compilation (`npx tsc --noEmit`) exits clean with no errors.

The phase is gated only on human UAT confirmation for items 1–9 above. Items 1–7 are carried forward from the previous verification. Items 8 and 9 are new, covering the delete flow fix from plan 04-05.

---

_Verified: 2026-03-16T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: after plan 04-05 gap closure (commit 4b80ae4) — delete button fix in MaterialLibrary.tsx_
