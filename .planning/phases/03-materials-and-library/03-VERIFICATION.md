---
phase: 03-materials-and-library
verified: 2026-03-15T21:30:00Z
status: human_needed
score: 14/14 must-haves verified
re_verification: false
human_verification:
  - test: "Upload a PDF or PPTX file on the dashboard"
    expected: "Upload returns immediately (under ~10s) with AI week suggestion inline. File input is visible below the syllabus WeekTimeline section."
    why_human: "Verifies non-blocking upload timing, real Bedrock API call, and visible UI state — cannot confirm with static analysis"
  - test: "Click 'Change week' after uploading, select a different week, then click 'Confirm'"
    expected: "Dropdown shows all syllabus weeks. Selected week updates inline without page navigation. A 'Processing...' badge appears immediately after confirm."
    why_human: "Verifies real-time UI state transitions and Bedrock/Lambda wiring in the running app"
  - test: "Wait 30-120s after confirming, watch the Processing badge"
    expected: "Badge transitions to 'Embedded' (green) on ready status. Requires deployed AWS stack with live EmbedWorkerFunction, S3 Vectors bucket, and Bedrock Titan Embed V2 access."
    why_human: "End-to-end embedding pipeline runs async on AWS; cannot verify S3 Vectors write locally"
  - test: "Upload a second file without confirming it. Check the library."
    expected: "Unconfirmed material appears under its AI-suggested week with an amber 'Unconfirmed' badge. All weeks from the syllabus are shown, including empty ones with 'no materials yet'."
    why_human: "Requires running app with real DynamoDB data to confirm library rendering"
  - test: "Click a confirmed material row in the library"
    expected: "The original PDF or PPTX opens in a new browser tab. Clicking again after 5+ minutes should still work (URL is generated fresh per click, ExpiresIn=300)."
    why_human: "Presigned URL freshness requires real S3 interaction; cannot verify URL expiry behavior statically"
---

# Phase 3: Materials and Library Verification Report

**Phase Goal:** Students can upload lecture slides and notes, have them assigned to a week automatically, and browse everything in a chronological course view
**Verified:** 2026-03-15T21:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

All automated checks pass. The phase goal is fully implemented in code with substantive, wired artifacts. The 5 remaining items require human verification against a running application (locally or on AWS).

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SAM template declares MaterialsBucket, MaterialsTable (with user_id GSI), and EmbedWorkerFunction | VERIFIED | template.yaml lines 105-166: all three resources present with correct configuration |
| 2 | requirements.txt includes boto3>=1.39.5, PyMuPDF, python-pptx | VERIFIED | requirements.txt line 5-7: all three present, no duplicate unpinned boto3 |
| 3 | SylliFunction has MATERIALS_BUCKET, MATERIALS_TABLE, EMBED_FUNCTION_NAME env vars and IAM policies for S3, DynamoDB, and lambda:InvokeFunction | VERIFIED | template.yaml lines 35-68: all env vars and policies present |
| 4 | EmbedWorkerFunction has MATERIALS_BUCKET, MATERIALS_TABLE, VECTOR_BUCKET_NAME, VECTOR_INDEX_NAME and IAM for S3 read, DynamoDB write, bedrock:InvokeModel, s3vectors:PutVectors | VERIFIED | template.yaml lines 113-136: all env vars and all four IAM actions present |
| 5 | POST /api/v1/materials accepts PDF or PPTX, uploads to S3, stores DynamoDB record, returns material_id + ai_suggested_week synchronously | VERIFIED | material_service.py upload_material() calls s3.put_object, suggest_week_for_material (Bedrock), store_material — all wired; materials.py endpoint registered in app.py |
| 6 | POST /api/v1/materials/{id}/confirm triggers async Lambda (InvocationType=Event), returns {embed_status: processing} | VERIFIED | material_service.py line 95: InvocationType="Event"; confirm endpoint returns processing status |
| 7 | GET /api/v1/materials queries user_id-index GSI (no table scan) | VERIFIED | dynamo_service.py line 114: IndexName="user_id-index" in list_materials_for_user |
| 8 | GET /api/v1/materials/{id}/status returns 404 on ownership mismatch | VERIFIED | get_material() returns None on ownership mismatch; endpoint raises HTTPException(404) |
| 9 | GET /api/v1/materials/{id}/view returns fresh presigned URL (ExpiresIn=300) per call | VERIFIED | material_service.py line 111: ExpiresIn=300 in generate_presigned_url |
| 10 | Embed worker extracts text (PDF/PPTX), chunks at 1500/200, embeds via Titan Embed V2, writes to S3 Vectors with metadata | VERIFIED | embedding_service.py: extract_text, chunk_text (CHUNK_SIZE=1500, CHUNK_OVERLAP=200), embed_text (titan-embed-text-v2:0), write_vectors_to_s3 (put_vectors with user_id/material_id/week_number/chunk_index/source_text[:500]) |
| 11 | Embed worker sets embed_status=error on any exception so frontend poll terminates | VERIFIED | embed_worker.py lines 37 and 83: update_material_embed_status("error") in both the None-item guard and the outer except block |
| 12 | MaterialUpload component: raw fetch for upload, inline confirm UI, 4s polling, clears on ready/error | VERIFIED | MaterialUpload.tsx: raw fetch line 65, apiFetch for confirm line 99, setInterval 4000ms line 131, clearInterval on ready/error lines 119-121 |
| 13 | MaterialLibrary renders all weeks including empty ones, Unconfirmed badge, click opens presigned URL in new tab | VERIFIED | MaterialLibrary.tsx: iterates all weekMap.weeks, "no materials yet" for empty, Unconfirmed badge line 85, window.open line 34 |
| 14 | Dashboard wires MaterialUpload and MaterialLibrary with syllabusId/materials state and fetchMaterials callback | VERIFIED | dashboard/page.tsx: imports both components, syllabusId state, materials state, fetchMaterials called in useEffect and passed as onMaterialUploaded/onRefresh |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/requirements.txt` | boto3>=1.39.5, PyMuPDF, python-pptx | VERIFIED | All three present, no duplicate boto3 |
| `template.yaml` | MaterialsBucket, MaterialsTable with GSI, EmbedWorkerFunction | VERIFIED | All resources declared at lines 105-166 |
| `backend/services/dynamo_service.py` | store_material, get_material, update_material_week, update_material_embed_status, list_materials_for_user | VERIFIED | All 5 functions present at lines 72-119 |
| `backend/services/material_service.py` | upload_material, confirm_material_week, get_presigned_url | VERIFIED | All 3 functions present, substantive |
| `backend/routers/materials.py` | 5 API endpoints for material management | VERIFIED | All 5 endpoints present and registered |
| `backend/app.py` | materials router at /api/v1 | VERIFIED | Line 19: `app.include_router(materials.router, prefix="/api/v1")` |
| `backend/services/embedding_service.py` | extract_text, chunk_text, embed_text, write_vectors_to_s3 | VERIFIED | All 4 functions present and substantive |
| `backend/workers/__init__.py` | Empty init for Python package | VERIFIED | File exists (empty) |
| `backend/workers/embed_worker.py` | lambda_handler with full pipeline | VERIFIED | Full pipeline: DynamoDB lookup → S3 download → extract → chunk → embed → S3 Vectors → status |
| `frontend/components/MaterialUpload.tsx` | Upload with inline week confirm and polling | VERIFIED | Full implementation, 224 lines, all behaviors wired |
| `frontend/components/MaterialLibrary.tsx` | Week-organized library view | VERIFIED | Full implementation, 107 lines, all badges and click handler wired |
| `frontend/app/dashboard/page.tsx` | Extended with MaterialUpload + MaterialLibrary | VERIFIED | Both components imported and rendered in JSX |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| template.yaml SylliFunction | EmbedWorkerFunction | EMBED_FUNCTION_NAME + lambda:InvokeFunction IAM | WIRED | EMBED_FUNCTION_NAME: !Ref EmbedWorkerFunction at line 37; lambda:InvokeFunction policy at lines 66-68 |
| template.yaml EmbedWorkerFunction | S3 Vectors | VECTOR_BUCKET_NAME + s3vectors:PutVectors | WIRED | VECTOR_BUCKET_NAME env var at line 119; s3vectors:PutVectors IAM at line 135 |
| backend/routers/materials.py confirm | lambda_client.invoke(InvocationType=Event) | material_service.confirm_material_week | WIRED | material_service.py line 93-95: InvocationType="Event" |
| backend/services/material_service.py | bedrock.converse (week suggestion) | suggest_week_for_material called in upload_material | WIRED | material_service.py line 57: `suggested_week = suggest_week_for_material(filename, week_map)` |
| backend/routers/materials.py list | dynamo_service.list_materials_for_user | GSI query on user_id-index | WIRED | dynamo_service.py line 114: IndexName="user_id-index" |
| backend/workers/embed_worker.py | backend/services/embedding_service.py | from services.embedding_service import extract_text, chunk_text, embed_text, write_vectors_to_s3 | WIRED | embed_worker.py line 7: all 4 functions imported and called in order |
| backend/services/embedding_service.py write_vectors_to_s3 | S3 Vectors s3vectors client | boto3.client('s3vectors').put_vectors() | WIRED | embedding_service.py lines 21, 96-100: lazy client creation and put_vectors call |
| backend/workers/embed_worker.py finally/except | dynamo_service.update_material_embed_status | sets embed_status='error' on exception | WIRED | embed_worker.py lines 37 and 83: two call sites for error status |
| frontend/components/MaterialUpload.tsx | POST /api/v1/materials | raw fetch with FormData + Authorization header | WIRED | MaterialUpload.tsx lines 59-70: raw fetch with Bearer token, no Content-Type set |
| frontend/components/MaterialUpload.tsx confirm | POST /api/v1/materials/{id}/confirm | apiFetch with {week_number} body | WIRED | MaterialUpload.tsx line 99: apiFetch to confirm endpoint |
| frontend/components/MaterialUpload.tsx polling | GET /api/v1/materials/{id}/status | setInterval every 4000ms, clearInterval on ready/error | WIRED | MaterialUpload.tsx lines 113-131: setInterval(4000), clearInterval on both ready and error |
| frontend/components/MaterialLibrary.tsx material row | GET /api/v1/materials/{id}/view | apiFetch on click, window.open | WIRED | MaterialLibrary.tsx lines 31-34: apiFetch /view, window.open(_blank) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MAT-01 | 03-01, 03-02, 03-04 | User can upload PDF or PPTX files as course materials | SATISFIED | S3 bucket, upload endpoint, file type validation, MaterialUpload component all implemented |
| MAT-02 | 03-02, 03-04 | AI suggests which unit/week an uploaded material belongs to | SATISFIED | suggest_week_for_material calls Bedrock Claude; week suggestion returned in upload response; shown inline in MaterialUpload |
| MAT-03 | 03-02, 03-04 | User can confirm or override the AI-suggested unit/week assignment | SATISFIED | confirm endpoint + MaterialUpload Confirm/Change week UI with dropdown from weekMap |
| MAT-04 | 03-01, 03-02, 03-03, 03-04 | Uploaded materials chunked and embedded asynchronously (non-blocking) | SATISFIED | InvocationType=Event async Lambda invocation in material_service.py; embed worker runs independently |
| MAT-05 | 03-01, 03-03 | Embeddings stored with user_id and unit/week metadata | SATISFIED | embedding_service.py write_vectors_to_s3 stores user_id, material_id, week_number, chunk_index, source_text in each vector's metadata |
| LIB-01 | 03-02, 03-04 | User can view all uploaded materials organized by unit/week in a chronological timeline | SATISFIED | MaterialLibrary iterates all weekMap.weeks in order; GET /api/v1/materials fetched via GSI (chronological order) |
| LIB-02 | 03-02, 03-04 | User can click a material in the library to view the original file | SATISFIED | MaterialLibrary handleOpenMaterial calls GET /view; window.open with presigned URL |

All 7 Phase 3 requirements are SATISFIED by the implementation. No orphaned requirements found — REQUIREMENTS.md traceability table maps all 7 IDs to Phase 3, and all 7 are claimed by plans 03-01 through 03-04.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `template.yaml` | 34 | `JWT_SECRET: "dev-secret-replace-for-prod"  # TODO: use SSM for prod` | Info | Hardcoded dev secret; known pre-existing issue from Phase 2, does not affect Phase 3 goal |
| `frontend/components/MaterialLibrary.tsx` | 55 | `return null` | Info | Intentional: guards the case where no syllabus is loaded yet. Not a stub. |

No blocker or warning anti-patterns found in Phase 3 artifacts.

### Human Verification Required

#### 1. Non-blocking Upload with AI Week Suggestion

**Test:** Log in, navigate to the dashboard. Upload a PDF or PPTX file in the "Upload Materials" section (visible after a syllabus is loaded).
**Expected:** Response returns immediately (under ~10 seconds) with an inline row showing the filename, AI-suggested week and topic, plus "Confirm" and "Change week" buttons. The file input does not hang while waiting for embedding.
**Why human:** Verifies real Bedrock API call timing, real S3 upload, and visible UI state — cannot confirm interactivity or latency with static analysis.

#### 2. Inline Week Confirmation Flow

**Test:** After uploading, click "Change week". Select a different week from the dropdown. Verify the week label updates immediately. Then click "Confirm".
**Expected:** Dropdown is populated with all weeks from the syllabus. Selected week changes inline without navigation. Clicking "Confirm" causes a gray "Processing..." badge to appear immediately.
**Why human:** UI state transitions and real API wiring require a running application to observe.

#### 3. Embed Status Polling Completion (Requires Deployed AWS Stack)

**Test:** After confirming, wait 30-120 seconds while "Processing..." is shown.
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

---

## Summary

Phase 3 is complete. All 14 observable truths verified, all 12 artifacts substantive and wired, all 7 requirements satisfied. The UAT plan (03-05) was auto-approved in `auto_advance` mode — the 5 human verification items above correspond to the deferred manual UAT steps that were not actually performed in that checkpoint.

**All automated checks pass.** The phase goal is implemented end-to-end. Human verification is required only to confirm the running application behaves as expected under real AWS/network conditions.

---

_Verified: 2026-03-15T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
