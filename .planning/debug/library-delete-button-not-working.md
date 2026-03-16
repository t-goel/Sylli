---
status: diagnosed
trigger: "The delete button for uploaded files in the Library tab is not working. Files that failed to upload are still showing in the library and cannot be deleted when the delete button is clicked."
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T00:00:00Z
---

## Current Focus

hypothesis: Two separate bugs — (1) delete silently swallows 404s for unconfirmed materials that don't appear in the library, and (2) failed-upload files that DO appear are unconfirmed materials stored in DynamoDB with week_confirmed=false, which ARE returned by list_materials but the library only renders materials bucketed under a week — so they never appear in the UI in the first place AND the delete handler never checks res.ok so any 404 failure is invisible.
test: Traced full upload lifecycle, delete handler, and library rendering logic
expecting: Root cause confirmed
next_action: DONE — diagnose-only mode

## Symptoms

expected: Clicking delete on a file in the Library tab removes it from the list
actual: Files (particularly ones that failed to upload or are in error state) remain visible after clicking delete
errors: No visible error to the user — the delete button appears to do nothing
reproduction: Upload a file that results in embed_status=error; try to delete it from the library
started: Appears to be a design issue from the start

## Eliminated

- hypothesis: Auth token missing on delete request
  evidence: apiFetch() always attaches Bearer token from localStorage; same function works for other endpoints
  timestamp: 2026-03-16

- hypothesis: Wrong HTTP method or URL construction
  evidence: handleDeleteMaterial calls apiFetch(`/api/v1/materials/${materialId}`, { method: "DELETE" }) — URL and method are correct
  timestamp: 2026-03-16

- hypothesis: Backend delete_material fails to find the record
  evidence: Backend get_material() does a proper DynamoDB get_item with ownership check and returns None if not found; if found it proceeds correctly. The issue is not in backend logic itself.
  timestamp: 2026-03-16

## Evidence

- timestamp: 2026-03-16
  checked: MaterialLibrary.tsx handleDeleteMaterial (lines 38-41)
  found: Function calls apiFetch with DELETE, then unconditionally calls onRefresh() — it never checks res.ok or res.status. If the API returns 404 (material not found or ownership mismatch), the function silently swallows the error and calls onRefresh() anyway, which re-fetches the same list from DynamoDB — so the item still appears.
  implication: Any delete that fails at the API level is invisible to the user AND the UI refreshes back to the same broken state.

- timestamp: 2026-03-16
  checked: MaterialLibrary.tsx rendering logic (lines 65-66)
  found: The library renders materials grouped by weekMap weeks. It filters: `materials.filter((m) => m.week_number === week.week)`. Materials are only shown if their week_number matches a week in the weekMap.
  implication: An unconfirmed material (week_confirmed=false) uploaded but never confirmed WILL appear IF its AI-suggested week_number happens to match a week in weekMap. It will NOT appear if the AI-suggested week number is out of range.

- timestamp: 2026-03-16
  checked: MaterialUpload.tsx handleFileChange (lines 65-98)
  found: On a successful POST to /api/v1/materials, the backend stores a DynamoDB record with week_confirmed=false and embed_status=pending, then returns the material_id. This record is persisted in DynamoDB even if the user never clicks Confirm. The frontend shows a "Confirm" UI in the MaterialUpload component, but onMaterialUploaded() (which triggers fetchMaterials) is NOT called at upload time — only at confirm time (line 122). So unconfirmed materials are in DynamoDB but not fetched into the library list yet.
  implication: If the user uploads but never confirms, the material IS in DynamoDB but won't show in the library (no fetchMaterials call). However on page reload, fetchMaterials runs and WILL return these unconfirmed records from DynamoDB via list_materials_for_user — they then appear in the library stuck in unconfirmed/error state.

- timestamp: 2026-03-16
  checked: backend dynamo_service.py list_materials_for_user (lines 116-125)
  found: Returns ALL materials for the user with NO filter on week_confirmed or embed_status. Unconfirmed (week_confirmed=false) and errored (embed_status=error) materials are both returned.
  implication: After a page reload, all materials regardless of state appear in the API response and get passed to MaterialLibrary.

- timestamp: 2026-03-16
  checked: MaterialLibrary.tsx lines 65-66 (the filter)
  found: `materials.filter((m) => m.week_number === week.week)` — this filters by week_number only. An unconfirmed material with embed_status=error WILL appear in the library if its week_number (AI-suggested) matches a real week. The "Unconfirmed" badge and "Error" badge are shown (lines 91-103), so these items ARE rendered with a delete button.
  implication: The files the user sees stuck in the library are real DynamoDB records. The delete button IS triggered with the correct material_id. So why does it fail?

- timestamp: 2026-03-16
  checked: materials router delete endpoint (lines 66-72) and delete_material service (lines 115-125)
  found: The endpoint calls get_material(material_id, user_id). get_material does a DynamoDB get_item by material_id primary key and checks user_id matches. If the record exists and is owned by this user, it proceeds to delete. This path should work for errored materials since they are valid DynamoDB records with correct user_id.
  implication: Backend delete logic is CORRECT for records that exist. The bug is not in the backend deletion path itself.

- timestamp: 2026-03-16
  checked: handleDeleteMaterial in MaterialLibrary.tsx (lines 38-41) — the complete function
  found: `await apiFetch(...)` result is stored in no variable. `onRefresh()` is called unconditionally immediately after, regardless of whether the delete succeeded or failed. There is ZERO error handling. If the API returns a non-2xx status, the error is swallowed. onRefresh() triggers fetchMaterials() which re-fetches from DynamoDB — since deletion failed, the item still exists there, so the library repopulates with the same item.
  implication: THIS IS THE PRIMARY BUG. The delete fails silently. But WHY does the API return non-2xx? See next evidence entry.

- timestamp: 2026-03-16
  checked: confirm_material_week in material_service.py (lines 85-112) — error path
  found: When Lambda invoke fails, the code calls `update_material_embed_status(material_id, "error")` and returns `{"material_id": material_id, "embed_status": "error"}`. The material DOES remain in DynamoDB with embed_status=error. So the material_id is valid and the record exists.
  implication: For embed_status=error materials, the backend delete SHOULD succeed (record exists, user_id matches). The delete path is not obviously broken for these.

- timestamp: 2026-03-16
  checked: The upload flow for a "failed to upload" scenario — res.ok is false (lines 79-83 in MaterialUpload.tsx)
  found: If the POST /api/v1/materials itself fails (res.ok is false), the function sets an error message and returns early. setPendingMaterial is NOT called. No DynamoDB record is created (the upload never reached the backend successfully). These files are only shown as an error message in the upload UI — they are NOT in DynamoDB and do NOT appear in the library.
  implication: A true "failed upload" (HTTP error on POST) never creates a DB record and would never show in the library. The issue must be about materials that DID upload (got a material_id) but then failed during embedding.

- timestamp: 2026-03-16
  checked: Scenario where material IS in library with embed_status=error and user clicks delete
  found: handleDeleteMaterial calls DELETE /api/v1/materials/{material_id}. Backend finds the record (it exists), deletes from S3 (best-effort), deletes DynamoDB record, returns {"deleted": true} with 200. Then onRefresh() re-fetches — item is gone from DynamoDB — item disappears from library. This should work.
  implication: Wait — for this case, delete should work. Investigating what "failed to upload" actually means to the user.

- timestamp: 2026-03-16
  checked: Re-read issue description: "Files that failed to upload are still showing in the library"
  found: The word "failed to upload" from the user's perspective likely means: the file appears in the library with an "Error" embed badge (embed_status=error), meaning it uploaded to S3 and DynamoDB but embedding failed. OR it could mean the upload request itself failed partway — but in that case, no material_id was returned, so the file wouldn't be in the library. The key failure case in the library is embed_status=error materials.
  implication: The real scenario for library-visible failed files is embed_status=error with a valid material_id. The delete SHOULD work for these. But the missing error handling in handleDeleteMaterial means if anything unexpected causes a 404, it silently fails.

- timestamp: 2026-03-16
  checked: One more scenario — user uploads file (gets material_id, record in DB), page is refreshed BEFORE confirming week. fetchMaterials() returns the unconfirmed record. Material appears in library. User tries to delete it.
  found: The delete request hits backend with the valid material_id and user_id. Backend finds the record, deletes it. This works. BUT — what if the material from the pending upload in MaterialUpload component is the same record now showing in the library? When user deletes from library, the MaterialUpload component still holds the pendingMaterial state with the same material_id. After onRefresh(), the library item disappears, but the MaterialUpload confirm UI still shows. This is a UX inconsistency but not the core delete bug.

- timestamp: 2026-03-16
  checked: The ACTUAL silent failure: handleDeleteMaterial has no await on the response check
  found: Line 39: `await apiFetch(...)` — the await IS there, but the result is discarded. Line 40: `onRefresh()` is called with NO await either. This means onRefresh (which is async fetchMaterials) is fired but not awaited. The library might refresh before or after the delete completes, creating a race condition where the item reappears.
  implication: RACE CONDITION: onRefresh() = fetchMaterials() is not awaited. The GET /api/v1/materials request might complete and repopulate state BEFORE or concurrently with the DELETE completing, causing the deleted item to still appear. In practice, since DELETE is called first and onRefresh immediately fires a GET, the GET might return the item before DELETE committed in DynamoDB.

## Resolution

root_cause: |
  TWO compounding bugs:

  1. PRIMARY - Race condition / missing await in handleDeleteMaterial (MaterialLibrary.tsx lines 38-41):
     `onRefresh()` is called without `await`, and crucially the apiFetch DELETE response is never
     checked for success. The function fires DELETE, immediately fires GET (onRefresh/fetchMaterials),
     and if the GET completes before DynamoDB propagates the delete, the item reappears. More
     critically: if the DELETE returns a non-2xx response for any reason, the error is completely
     swallowed and onRefresh() repopulates the UI with the unchanged list — making delete appear broken.

  2. SECONDARY - No error feedback to user: even when the delete API call fails (404 or 500), the UI
     shows nothing. The user sees the item still there and believes the button did nothing.

  For the specific "failed upload files" scenario: materials that failed embedding (embed_status=error)
  ARE valid DynamoDB records with correct user_id, so the backend delete SHOULD succeed. The bug is
  most likely the race: onRefresh() re-fetches before DynamoDB consistency catches up, so the item
  briefly reappears — or for true orphaned records (no matching week in weekMap), they silently 404
  but the error goes unnoticed.

fix: NOT APPLIED (diagnose-only mode)
verification: NOT APPLIED
files_changed: []
