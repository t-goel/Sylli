---
status: verifying
trigger: "After pressing the X button to delete a material in the library, the item remains visible in the UI — it doesn't disappear."
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED ROOT CAUSE (REAL) - Lambda IAM role is missing dynamodb:DeleteItem permission. DynamoDBWritePolicy does NOT include DeleteItem. CloudWatch logs prove: AccessDeniedException on DeleteItem call. This is why backend returns HTTP 500.
test: CloudWatch logs filter-log-events on DELETE requests — error message is unambiguous.
expecting: Adding explicit dynamodb:DeleteItem IAM statement to template.yaml and redeploying will fix the 500.
next_action: Fix template.yaml to add DeleteItem permission, redeploy

## Symptoms

expected: Pressing X on a material removes it from the library list visually
actual: The item stays in the list after pressing X (no visual removal)
errors: Unknown — user hasn't reported console errors
reproduction: Press X on any material in the library tab on the deployed app
started: Reported after Phase 5 deployment (may have been present before)

## Eliminated

- hypothesis: handleDeleteMaterial silently swallows errors / no error handling (prior session bug)
  evidence: Current MaterialLibrary.tsx (lines 58-73) has COMPLETE error handling: checks res.ok, parses error body, sets deleteError state, returns early on failure. The prior session's diagnosis of missing error handling has already been fixed.
  timestamp: 2026-03-16

- hypothesis: onRefresh not awaited (prior session race condition)
  evidence: Current MaterialLibrary.tsx line 69: `await onRefresh()` — the await IS present. Prior session's secondary fix was applied.
  timestamp: 2026-03-16

- hypothesis: Backend delete_material is broken (code logic)
  evidence: delete_material in material_service.py (lines 115-125) correctly calls get_material for ownership check, then S3 delete (best-effort), then _delete_material_record. dynamo_service.delete_material (lines 110-113) calls table.delete_item correctly. Backend code logic is sound.
  timestamp: 2026-03-16

- hypothesis: Frontend fix (optimistic removal) was never committed/pushed
  evidence: CloudWatch logs prove the DELETE request reaches the Lambda and crashes with AccessDeniedException BEFORE any frontend rendering issue. The frontend commit status is irrelevant until the backend 500 is fixed.
  timestamp: 2026-03-16

- hypothesis: IAM DynamoDBWritePolicy includes DeleteItem
  evidence: CloudWatch log entry: "AccessDeniedException when calling the DeleteItem operation: User ... is not authorized to perform: dynamodb:DeleteItem ... because no identity-based policy allows the dynamodb:DeleteItem action". DynamoDBWritePolicy does NOT include DeleteItem despite AWS documentation implying it does. The deployed role is missing this permission.
  timestamp: 2026-03-16

## Evidence

- timestamp: 2026-03-16T01:00:00Z
  checked: handleDeleteSuccess in dashboard/page.tsx (lines 70-76) after human verified fix did not work
  found: setMaterials(filter) called on line 74, then fetchMaterials() called immediately on line 75 without await. fetchMaterials() fires a GET /api/v1/materials. The fetch resolves and calls setMaterials(data.materials) — which includes the deleted item (DynamoDB GSI hasn't propagated yet). This second setMaterials call OVERWRITES the optimistic filter. React renders twice: once with item removed (good), then immediately with item present (bad). The user sees the item stay because the second render wins.
  implication: The fix was logically sound in theory but self-defeating in practice — the "background refresh" immediately undoes the optimistic removal. The fetchMaterials() call must be removed from handleDeleteSuccess entirely.

- timestamp: 2026-03-16
  checked: MaterialLibrary.tsx handleDeleteMaterial (lines 58-73) — full current code
  found: Function is fully correct: guard against concurrent deletes, setDeletingId, apiFetch DELETE, checks res.ok with error state, then `await onRefresh()`, finally block clears deletingId. This is the FIXED version — prior bugs are resolved.
  implication: The delete flow in MaterialLibrary.tsx is correct. The issue must be elsewhere.

- timestamp: 2026-03-16
  checked: dashboard/page.tsx onRefresh prop (line 152) and fetchMaterials function (lines 55-61)
  found: `onRefresh={fetchMaterials}` — fetchMaterials is an async function. Inside, it calls `setMaterials(data.materials ?? [])`. CRITICAL OBSERVATION: `fetchMaterials` is a plain async function declared inside the component. When called as `await onRefresh()` from MaterialLibrary, it awaits the Promise returned by fetchMaterials. That Promise resolves after `setMaterials(...)` is called — but `setMaterials` is asynchronous in React (it schedules a re-render, doesn't apply immediately). So `await onRefresh()` completes BEFORE the new state is actually rendered. This is not a bug per se — React batches state updates and will re-render, and the deleted item won't be in the new state.
  implication: The state update mechanism is correct. React WILL re-render with the new list after fetchMaterials completes. The delete should visually disappear.

- timestamp: 2026-03-16
  checked: The CORS fix from the prior commit (da205c2) — "add global exception handler and Gateway Response CORS headers for delete button"
  found: The previous debug session for "Failed to Fetch" was resolved by adding CORS headers. This means the DELETE request was previously failing entirely (CORS preflight failure → "Failed to Fetch" error). That is now fixed.
  implication: The delete should be reaching the backend now. But the current symptom is that the item STAYS visible — suggesting either (a) the delete IS succeeding on backend but UI isn't updating, or (b) the delete is STILL failing with a non-CORS error that's being caught and shown as deleteError (but user says no visible error), or (c) something else.

- timestamp: 2026-03-16
  checked: MaterialLibrary.tsx deletingId guard (line 59) and disabled state (line 125)
  found: `if (deletingId !== null) return` — if a delete is in progress for ANY material, clicking X on any material does nothing. The button is only disabled for `deletingId === material.material_id` (line 125), not ALL buttons. But the guard at line 59 prevents concurrent operations. After the operation, `finally { setDeletingId(null) }` clears the guard.
  implication: No infinite loop or permanent lock. The guard resets correctly.

- timestamp: 2026-03-16
  checked: What happens if onRefresh (fetchMaterials) is NOT async-awaitable — i.e., what if the dashboard passes a non-async wrapper
  found: dashboard line 152: `onRefresh={fetchMaterials}` — fetchMaterials IS declared as `async function fetchMaterials()` at line 55. So it returns a Promise. `await onRefresh()` in MaterialLibrary will correctly await it. No issue here.
  implication: The await chain is correct.

- timestamp: 2026-03-16
  checked: git status and git log for frontend files after human checkpoint reported fix had no effect
  found: `git status` shows both frontend/app/dashboard/page.tsx and frontend/components/MaterialLibrary.tsx as "modified" (unstaged). `git log --all -- frontend/app/dashboard/page.tsx` shows last commit touching these files was 41b8814 ("complete phase 4"). The fix commits da205c2 and 6d42162 only changed backend/app.py, template.yaml, and a planning doc — zero frontend changes. The working directory has the correct fix but it was NEVER committed or pushed to the remote.
  implication: REAL ROOT CAUSE OF PERSISTENCE: The deployment runs the committed code. The frontend fix lived only in the local working directory. Every "fix was applied" was actually only applied locally — the deployment continued serving the old onRefresh={fetchMaterials} code that triggers the GSI race condition. The fix is correct; the problem is it was never deployed.

- timestamp: 2026-03-16
  checked: Whether the item could be re-appearing because fetchMaterials re-fetches and the DynamoDB delete hasn't propagated yet
  found: DynamoDB is eventually consistent for GSI queries (list_materials_for_user uses a GSI query on user_id-index). After a delete_item on the base table, the GSI may still return the deleted item for a short window. fetchMaterials queries the GSI via list_materials_for_user. If the GET /api/v1/materials is called immediately after DELETE, DynamoDB GSI inconsistency could return the deleted item, causing it to reappear in state.
  implication: THIS IS THE ROOT CAUSE. The item is deleted from DynamoDB base table but the GSI hasn't caught up. fetchMaterials re-fetches via GSI → deleted item still returned → state updated WITH the deleted item → no visual removal.

- timestamp: 2026-03-16
  checked: template.yaml MaterialsTable GSI definition (lines 181-189)
  found: GlobalSecondaryIndex `user_id-index` has ProjectionType=ALL and no special consistency settings. DynamoDB GSI reads are eventually consistent by default — there is no ConsistentRead option for GSI queries (unlike base table GetItem). The window is typically milliseconds to ~1 second but can be longer.
  implication: Confirms GSI eventual consistency is unavoidable for the list query. The fix must be at the frontend layer: optimistic state removal so the UI doesn't depend on the GSI being immediately consistent.

- timestamp: 2026-03-16
  checked: Fix design — two options
  found: Option A: Change onRefresh prop to onDeleteSuccess(materialId) in MaterialLibrary; dashboard handles by filtering state. Option B: In MaterialLibrary, after successful delete, optimistically filter the passed materials prop (not possible — materials is read-only prop). Option C: Change MaterialLibrary to call both a remove callback AND onRefresh, where the dashboard removes the item from state instantly and schedules a background refresh. Option A is cleanest and minimal.
  implication: Use Option A — replace onRefresh with onDeleteSuccess(materialId: string) in MaterialLibrary, implement in dashboard as instant state filter + background fetchMaterials.

- timestamp: 2026-03-16T(current)
  checked: CloudWatch logs for /aws/lambda/Sylli-SylliFunction-1vh4l0UEOjkk filtered on DELETE
  found: "Unhandled exception on DELETE /api/v1/materials/{material_id}: An error occurred (AccessDeniedException) when calling the DeleteItem operation: User: arn:aws:sts::727494188797:assumed-role/Sylli-SylliFunctionRole-MvGzHQB534jZ/Sylli-SylliFunction-1vh4l0UEOjkk is not authorized to perform: dynamodb:DeleteItem on resource: arn:aws:dynamodb:us-east-1:727494188797:table/sylli-materials-table because no identity-based policy allows the dynamodb:DeleteItem action"
  implication: DEFINITIVE ROOT CAUSE. Every DELETE call fails at the DynamoDB layer with an IAM permission error. DynamoDBWritePolicy does not include DeleteItem. The fix is adding an explicit IAM statement for dynamodb:DeleteItem in template.yaml.

## Resolution

root_cause: |
  Lambda IAM role is missing the dynamodb:DeleteItem permission on sylli-materials-table.
  The DynamoDBWritePolicy SAM managed policy does NOT grant DeleteItem — only PutItem,
  UpdateItem, BatchWriteItem, etc. Every DELETE /api/v1/materials/{material_id} request
  reaches the Lambda, passes auth middleware, calls dynamo_service.delete_material, and
  then crashes with AccessDeniedException at table.delete_item(). The Lambda's global
  exception handler catches this and returns HTTP 500 with CORS headers intact.
  CloudWatch log (2026-03-17T03:37:30Z): "AccessDeniedException when calling the DeleteItem
  operation: User ... is not authorized to perform: dynamodb:DeleteItem on resource:
  arn:aws:dynamodb:us-east-1:727494188797:table/sylli-materials-table because no
  identity-based policy allows the dynamodb:DeleteItem action"

fix: |
  Added explicit IAM Statement to SylliFunction policies in template.yaml:
    - Effect: Allow
      Action: [dynamodb:DeleteItem]
      Resource: !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/sylli-materials-table"
  This grants the Lambda role the missing permission. Requires sam deploy to take effect.

verification: |
  Self-verified:
  - CloudWatch log confirms exact error: AccessDeniedException on DeleteItem
  - template.yaml diff shows correct addition of DeleteItem statement
  - Awaiting sam deploy and human verification that DELETE returns 200

files_changed:
  - template.yaml
