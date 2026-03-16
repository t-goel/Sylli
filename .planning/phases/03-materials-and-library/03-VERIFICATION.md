---
phase: 03-materials-and-library
verified: 2026-03-15T22:00:00Z
status: human_needed
score: 17/17 must-haves verified
re_verification: true
  previous_status: human_needed
  previous_score: 14/14
  gaps_closed:
    - "confirm_material_week returns embed_status tied to actual Lambda invoke outcome (not env var truthiness) — 03-06 bug fix verified"
    - "Frontend correctly handles 'pending' response from confirm: shows 'Confirmed — embedding queued', clears row after 1.5s, does not start polling"
    - "Frontend polling correctly handles 'pending' status during poll: stops loop, does not show permanent 'Embedding failed'"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Upload a PDF or PPTX file on the dashboard"
    expected: "Upload returns immediately (under ~10s) with AI week suggestion inline. File input is visible below the syllabus WeekTimeline section."
    why_human: "Verifies non-blocking upload timing, real Bedrock API call, and visible UI state — cannot confirm with static analysis"
  - test: "Click 'Change week' after uploading, select a different week, then click 'Confirm'"
    expected: "Dropdown shows all syllabus weeks. Selected week updates inline without page navigation. A 'Processing...' badge appears immediately after confirm (or 'Confirmed — embedding queued' in local dev where EMBED_FUNCTION_NAME is unset)."
    why_human: "Verifies real-time UI state transitions and Bedrock/Lambda wiring in the running app"
  - test: "Wait 30-120s after confirming (deployed stack only), watch the Processing badge"
    expected: "Badge transitions to 'Embedded' (green) on ready status. Requires deployed AWS stack with live EmbedWorkerFunction, S3 Vectors bucket, and Bedrock Titan Embed V2 access."
    why_human: "End-to-end embedding pipeline runs async on AWS; cannot verify S3 Vectors write locally"
  - test: "Upload a second file without confirming it. Check the library."
    expected: "Unconfirmed material appears under its AI-suggested week with an amber 'Unconfirmed' badge. All weeks from the syllabus are shown, including empty ones with 'no materials yet'."
    why_human: "Requires running app with real DynamoDB data to confirm library rendering"
  - test: "Click a confirmed material row in the library"
    expected: "The original PDF or PPTX opens in a new browser tab. Clicking again after 5+ minutes should still work (URL is generated fresh per click, ExpiresIn=300)."
    why_human: "Presigned URL freshness requires real S3 interaction; cannot verify URL expiry behavior statically"
  - test: "Run locally with EMBED_FUNCTION_NAME unset. Upload and Confirm a file."
    expected: "Confirm response returns embed_status='pending'. Frontend shows 'Confirmed — embedding queued' in gray text, then clears the row after ~1.5s. 'Embedding failed' must NOT appear."
    why_human: "03-06 fix correctness under local dev conditions requires a running app to confirm the UI branch fires as expected"
---

# Phase 3: Materials and Library Verification Report

**Phase Goal:** Build the materials upload, processing, and library features so users can upload PDFs/PPTXs, have them embedded asynchronously, and browse materials by week.
**Verified:** 2026-03-15T22:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after 03-06 gap closure (confirm embed_status bug fix)

## Re-verification Summary

This is a re-verification following plan 03-06 (commit `ce30167`), which fixed a bug where `confirm_material_week` returned `embed_status="processing"` based on `EMBED_FUNCTION_NAME` env var truthiness rather than whether `lambda_client.invoke()` actually succeeded. The previous VERIFICATION.md (also 2026-03-15) had `status: human_needed` with no automated gaps — this re-verification confirms the 03-06 fix is in place, verifies 3 new must-haves from the gap closure plan, and runs regression checks on all 14 previously verified truths.

**All 17 must-haves verified. No regressions. No new gaps.**

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SAM template declares MaterialsBucket, MaterialsTable (with user_id GSI), and EmbedWorkerFunction | VERIFIED | template.yaml lines 105-166: all three resources present with correct configuration |
| 2 | requirements.txt includes boto3>=1.39.5, PyMuPDF, python-pptx | VERIFIED | requirements.txt lines 5-7: all three present, no duplicate unpinned boto3 |
| 3 | SylliFunction has MATERIALS_BUCKET, MATERIALS_TABLE, EMBED_FUNCTION_NAME env vars and IAM policies for S3, DynamoDB, and lambda:InvokeFunction | VERIFIED | template.yaml lines 35-68: all env vars at lines 35-37, lambda:InvokeFunction at lines 67-68 |
| 4 | EmbedWorkerFunction has MATERIALS_BUCKET, MATERIALS_TABLE, VECTOR_BUCKET_NAME, VECTOR_INDEX_NAME and IAM for S3 read, DynamoDB write, bedrock:InvokeModel, s3vectors:PutVectors | VERIFIED | template.yaml lines 116-135: all env vars and all four IAM actions present |
| 5 | POST /api/v1/materials accepts PDF or PPTX, uploads to S3, stores DynamoDB record, returns material_id + ai_suggested_week synchronously | VERIFIED | material_service.py upload_material() calls s3.put_object, suggest_week_for_material (Bedrock), store_material — all wired; materials.py endpoint registered in app.py |
| 6 | POST /api/v1/materials/{id}/confirm triggers async Lambda (InvocationType=Event), returns {embed_status: processing} when invoke succeeds | VERIFIED | material_service.py lines 91-107: invoked boolean gate; InvocationType="Event" line 98; returns "processing" only when invoked=True (03-06 fix) |
| 7 | GET /api/v1/materials queries user_id-index GSI (no table scan) | VERIFIED | dynamo_service.py line 120: IndexName="user_id-index" in list_materials_for_user |
| 8 | GET /api/v1/materials/{id}/status returns 404 on ownership mismatch | VERIFIED | get_material() returns None on ownership mismatch; endpoint raises HTTPException(404) at materials.py line 63 |
| 9 | GET /api/v1/materials/{id}/view returns fresh presigned URL (ExpiresIn=300) per call | VERIFIED | material_service.py line 133: ExpiresIn=300 in generate_presigned_url |
| 10 | Embed worker extracts text (PDF/PPTX/DOCX), chunks at 1500/200, embeds via Titan Embed V2, writes to S3 Vectors with metadata | VERIFIED | embedding_service.py: extract_text handles pdf/pptx/docx, CHUNK_SIZE=1500 CHUNK_OVERLAP=200, embed_text uses amazon.titan-embed-text-v2:0, write_vectors_to_s3 puts vectors with user_id/material_id/week_number/chunk_index/source_text[:500] |
| 11 | Embed worker sets embed_status=error on any exception so frontend poll terminates | VERIFIED | embed_worker.py lines 37 and 83: update_material_embed_status("error") in both the None-item guard and the outer except block |
| 12 | MaterialUpload component: raw fetch for upload, inline confirm UI, 4s polling, clears on ready/error | VERIFIED | MaterialUpload.tsx: raw fetch line 72, apiFetch for confirm line 106, setInterval 4000ms line 173, clearInterval on ready/error lines 158-165 |
| 13 | MaterialLibrary renders all weeks including empty ones, Unconfirmed badge, click opens presigned URL in new tab | VERIFIED | MaterialLibrary.tsx: iterates all weekMap.weeks, "no materials yet" for empty (line 76), Unconfirmed badge lines 91-95, window.open line 34 |
| 14 | Dashboard wires MaterialUpload and MaterialLibrary with syllabusId/materials state and fetchMaterials callback | VERIFIED | dashboard/page.tsx: imports both components, syllabusId state (line 35), materials state (line 36), fetchMaterials called in useEffect and passed as onMaterialUploaded/onRefresh |
| 15 (NEW) | confirm_material_week returns "processing" only when lambda_client.invoke() actually succeeds | VERIFIED | material_service.py lines 91-107: invoked=False initialized, invoked=True set only after invoke() and update_material_embed_status() both succeed; return uses "processing" if invoked else "pending" — old EMBED_FUNCTION_NAME-based return line is gone |
| 16 (NEW) | Frontend skips polling loop when confirm returns embed_status != "processing" | VERIFIED | MaterialUpload.tsx lines 125-131: `if (initialStatus !== "processing") { setTimeout(clear, 1500); return }` — exits handleConfirm before setInterval |
| 17 (NEW) | Frontend shows "Confirmed — embedding queued" (not "Embedding failed") when embed_status is "pending" | VERIFIED | MaterialUpload.tsx line 253-254: `{embedStatus === "pending" && <p>Confirmed — embedding queued</p>}` — separate render branch from error |

**Score:** 17/17 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/requirements.txt` | boto3>=1.39.5, PyMuPDF, python-pptx | VERIFIED | All three present; python-docx also present; no unpinned boto3 |
| `template.yaml` | MaterialsBucket, MaterialsTable with GSI, EmbedWorkerFunction | VERIFIED | All resources declared; GSI at line 159 |
| `backend/services/dynamo_service.py` | store_material, get_material, update_material_week, update_material_embed_status, list_materials_for_user | VERIFIED | All 5 functions present at lines 72-125 |
| `backend/services/material_service.py` | upload_material, confirm_material_week (with invoked gate), get_presigned_url | VERIFIED | All 3 functions present and substantive; 03-06 fix at lines 91-107 |
| `backend/routers/materials.py` | 5+ API endpoints for material management | VERIFIED | 6 endpoints present: POST /materials, POST /materials/{id}/confirm, GET /materials, GET /materials/{id}/status, DELETE /materials/{id}, GET /materials/{id}/view |
| `backend/app.py` | materials router at /api/v1 | VERIFIED | Line 19: `app.include_router(materials.router, prefix="/api/v1")` |
| `backend/services/embedding_service.py` | extract_text, chunk_text, embed_text, write_vectors_to_s3 | VERIFIED | All 4 functions present and substantive; DOCX support added |
| `backend/workers/__init__.py` | Empty init for Python package | VERIFIED | File exists |
| `backend/workers/embed_worker.py` | lambda_handler with full pipeline | VERIFIED | Full pipeline: DynamoDB lookup -> S3 download -> extract -> chunk -> embed -> S3 Vectors -> status update |
| `frontend/components/MaterialUpload.tsx` | Upload with inline week confirm, polling, local-dev fallback handling | VERIFIED | Full implementation, 269 lines, all behaviors wired including 03-06 frontend fixes |
| `frontend/components/MaterialLibrary.tsx` | Week-organized library view with delete | VERIFIED | Full implementation, 121 lines, all badges and click handler wired; delete button added |
| `frontend/app/dashboard/page.tsx` | Extended with MaterialUpload + MaterialLibrary | VERIFIED | Both components imported and rendered in JSX; fetchMaterials wired as callbacks |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| template.yaml SylliFunction | EmbedWorkerFunction | EMBED_FUNCTION_NAME + lambda:InvokeFunction IAM | WIRED | EMBED_FUNCTION_NAME: !Ref EmbedWorkerFunction at line 37; lambda:InvokeFunction policy at lines 67-68 |
| template.yaml EmbedWorkerFunction | S3 Vectors | VECTOR_BUCKET_NAME + s3vectors:PutVectors | WIRED | VECTOR_BUCKET_NAME env var at line 118; s3vectors:PutVectors IAM at line 135 |
| backend/routers/materials.py confirm | lambda_client.invoke(InvocationType=Event) | material_service.confirm_material_week | WIRED | material_service.py line 95-99: InvocationType="Event"; invoked=True gate at line 102 |
| backend/services/material_service.py confirm_material_week | update_material_embed_status | invoked boolean gate (03-06 fix) | WIRED | material_service.py lines 91-107: invoked=False -> invoke() -> update_status -> invoked=True -> return based on invoked |
| backend/services/material_service.py | bedrock.converse (week suggestion) | suggest_week_for_material called in upload_material | WIRED | material_service.py line 57: `suggested_week = suggest_week_for_material(filename, week_map)` |
| backend/routers/materials.py list | dynamo_service.list_materials_for_user | GSI query on user_id-index | WIRED | dynamo_service.py line 120: IndexName="user_id-index" |
| backend/workers/embed_worker.py | backend/services/embedding_service.py | from services.embedding_service import extract_text, chunk_text, embed_text, write_vectors_to_s3 | WIRED | embed_worker.py line 7: all 4 functions imported and called in order at lines 48, 58, 61, 64 |
| backend/services/embedding_service.py write_vectors_to_s3 | S3 Vectors s3vectors client | boto3.client('s3vectors').put_vectors() | WIRED | embedding_service.py lines 21, 100-104: lazy client creation (_get_s3v) and put_vectors call |
| backend/workers/embed_worker.py finally/except | dynamo_service.update_material_embed_status | sets embed_status='error' on exception | WIRED | embed_worker.py lines 37 and 83: two call sites for error status |
| frontend/components/MaterialUpload.tsx | POST /api/v1/materials | raw fetch with FormData + Authorization header | WIRED | MaterialUpload.tsx lines 72-77: raw fetch with Bearer token, no Content-Type set |
| frontend/components/MaterialUpload.tsx confirm | POST /api/v1/materials/{id}/confirm | apiFetch with {week_number} body | WIRED | MaterialUpload.tsx line 106: apiFetch to confirm endpoint |
| frontend/components/MaterialUpload.tsx | polling vs. local-dev branch | initialStatus check gates setInterval | WIRED | MaterialUpload.tsx lines 118-131: initialStatus from confirmData.embed_status; if "pending" → setTimeout+return, if "processing" → setInterval |
| frontend/components/MaterialUpload.tsx polling | GET /api/v1/materials/{id}/status | setInterval every 4000ms, clearInterval on ready/error | WIRED | MaterialUpload.tsx lines 135-173: setInterval(4000), clearInterval on both ready and error, timeout at 5min |
| frontend/components/MaterialLibrary.tsx material row | GET /api/v1/materials/{id}/view | apiFetch on click, window.open | WIRED | MaterialLibrary.tsx lines 31-34: apiFetch /view, window.open(_blank) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MAT-01 | 03-01, 03-02, 03-04 | User can upload PDF or PPTX files as course materials | SATISFIED | S3 bucket, upload endpoint with ALLOWED_EXTENSIONS check (.pdf/.pptx/.docx), MaterialUpload component all implemented |
| MAT-02 | 03-02, 03-04 | AI suggests which unit/week an uploaded material belongs to | SATISFIED | suggest_week_for_material calls Bedrock Claude (bedrock_service.MODEL_ID); week suggestion returned in upload response and shown inline in MaterialUpload |
| MAT-03 | 03-02, 03-04, 03-06 | User can confirm or override the AI-suggested unit/week assignment | SATISFIED | confirm endpoint + MaterialUpload Confirm/Change week UI with dropdown from weekMap; 03-06 fixed the embed_status return value to match actual invoke outcome |
| MAT-04 | 03-01, 03-02, 03-03, 03-04 | Uploaded materials chunked and embedded asynchronously (non-blocking) | SATISFIED | InvocationType=Event async Lambda invocation in material_service.py; embed worker runs independently; upload endpoint returns before embedding starts |
| MAT-05 | 03-01, 03-03 | Embeddings stored with user_id and unit/week metadata | SATISFIED | embedding_service.py write_vectors_to_s3 stores user_id, material_id, week_number, chunk_index, source_text in each vector's metadata |
| LIB-01 | 03-02, 03-04 | User can view all uploaded materials organized by unit/week in a chronological timeline | SATISFIED | MaterialLibrary iterates all weekMap.weeks in order; GET /api/v1/materials fetched via GSI with ScanIndexForward=True (chronological order) |
| LIB-02 | 03-02, 03-04 | User can click a material in the library to view the original file | SATISFIED | MaterialLibrary handleOpenMaterial calls GET /view; window.open with presigned URL |

All 7 Phase 3 requirements are SATISFIED. No orphaned requirements — REQUIREMENTS.md traceability table marks all 7 as Phase 3/Complete. LIB-01 and LIB-02 are claimed by plans 03-02 and 03-04 even though the prompt listed only MAT-01 through MAT-05; both are fully satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `template.yaml` | 34 | `JWT_SECRET: "dev-secret-replace-for-prod"  # TODO: use SSM for prod` | Info | Hardcoded dev secret; known pre-existing issue from Phase 2, does not affect Phase 3 goal |
| `frontend/components/MaterialLibrary.tsx` | 59 | `return null` | Info | Intentional: guards the case where no syllabus is loaded yet. Not a stub. |
| `frontend/components/MaterialLibrary.tsx` | 17 | `file_type: "pdf" \| "pptx"` (missing "docx") | Warning | Type inconsistency: upload now accepts .docx but MaterialLibrary Material interface omits "docx". DOCX files will match the PPT badge branch. No runtime crash but misleading badge label. Does not block Phase 3 goal. |

No blocker anti-patterns found. The docx type gap is a warning that may surface in Phase 4 or a follow-up polish pass.

### Human Verification Required

#### 1. Non-blocking Upload with AI Week Suggestion

**Test:** Log in, navigate to the dashboard. Upload a PDF or PPTX file in the "Upload Materials" section (visible after a syllabus is loaded).
**Expected:** Response returns immediately (under ~10 seconds) with an inline row showing the filename, AI-suggested week and topic, plus "Confirm" and "Change week" buttons.
**Why human:** Verifies real Bedrock API call timing, real S3 upload, and visible UI state — cannot confirm interactivity or latency with static analysis.

#### 2. Inline Week Confirmation Flow

**Test:** After uploading, click "Change week". Select a different week from the dropdown. Verify the week label updates immediately. Then click "Confirm".
**Expected:** Dropdown is populated with all weeks from the syllabus. Selected week changes inline without navigation. Clicking "Confirm" causes either a gray "Processing..." badge (deployed AWS stack) or "Confirmed — embedding queued" text (local dev, EMBED_FUNCTION_NAME unset) to appear immediately.
**Why human:** UI state transitions and real API wiring require a running application to observe. The 03-06 fix must be confirmed to eliminate the previous "Embedding failed" false positive.

#### 3. Embed Status Polling Completion (Requires Deployed AWS Stack)

**Test:** After confirming on a deployed stack, wait 30-120 seconds while "Processing..." is shown.
**Expected:** Badge transitions to green "Embedded" text. Requires deployed EmbedWorkerFunction, S3 Vectors bucket (`sylli-vectors`), and Bedrock Titan Embed V2 access in AWS.
**Why human:** Async Lambda execution and S3 Vectors writes cannot be simulated locally; requires real AWS stack.

#### 4. Library — All Weeks Including Empty Ones

**Test:** Ensure a syllabus is loaded. Scroll to the "Course Materials" section.
**Expected:** Every week from the syllabus appears as a section header. Weeks with no uploaded materials show "no materials yet" in gray text.
**Why human:** Requires real DynamoDB data and running frontend to verify rendering.

#### 5. Click-to-View Presigned URL

**Test:** Click a confirmed material row in the library.
**Expected:** The original file opens in a new browser tab. Clicking again 5+ minutes later should still open the file (URL is generated fresh on each click, not cached).
**Why human:** Presigned URL freshness requires real S3 interaction; ExpiresIn=300 means URLs expire in 5 minutes so repeated clicking confirms fresh generation.

#### 6. Local Dev Confirm — No False "Embedding Failed"

**Test:** With EMBED_FUNCTION_NAME env var unset (local `sam local start-api` or `uvicorn` without the Lambda env var), upload a file and click Confirm.
**Expected:** Confirm returns `embed_status="pending"`. Frontend immediately shows "Confirmed — embedding queued" in gray text, then clears the row after ~1.5 seconds. "Embedding failed" must NOT appear.
**Why human:** Directly validates the 03-06 fix under local dev conditions. Cannot be confirmed through static analysis alone.

---

## Summary

Phase 3 re-verification complete. All 17 observable truths verified (14 from initial verification + 3 new truths from 03-06 gap closure). All 12 artifacts are substantive and wired. All 7 requirements are satisfied. The 03-06 bug fix (commit `ce30167`) is confirmed in place: `material_service.py` uses the `invoked` boolean gate and `MaterialUpload.tsx` correctly branches on `initialStatus !== "processing"` to avoid the polling loop in local dev.

The one new warning found (docx file_type missing from MaterialLibrary interface) is minor and does not block the phase goal — DOCX files display with a PPT badge rather than a missing-type crash.

**All automated checks pass.** Phase goal is implemented end-to-end. Human verification is required to confirm the running application behaves correctly under real AWS/network conditions and that the 03-06 fix eliminates the false "Embedding failed" in local dev.

---

_Verified: 2026-03-15T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
