---
status: diagnosed
trigger: "Test 3 in UAT — upload a file, get AI week suggestion, click Confirm — shows 'embedding failed' and disappears instead of 'Processing...'"
created: 2026-03-15T00:00:00Z
updated: 2026-03-15T00:00:00Z
---

## Current Focus

hypothesis: Backend returns embed_status="pending" (not "processing") in the confirm response when EMBED_FUNCTION_NAME is set but Lambda invocation fails silently. Frontend then immediately enters the "pending" polling path, hits the else-if branch at the first poll, and transitions to embed_status="error", then clears the row.
test: Confirmed by reading backend logic vs frontend polling logic
expecting: Root cause confirmed — no further testing needed
next_action: Return ROOT CAUSE FOUND

## Symptoms

expected: Click Confirm. The Confirm/Change week buttons disappear and a gray "Processing..." text appears immediately in the upload row.
actual: "it just says embedding failed and then disappears"
errors: "Embedding failed" text appears in the upload row, then disappears
reproduction: Upload a file, get AI week suggestion, click Confirm (Test 3 in UAT)
started: Discovered during UAT

## Eliminated

- hypothesis: Backend returns 4xx/5xx error on confirm, causing res.ok to be false
  evidence: The confirm endpoint only returns 404 if material not found; the material exists at this point. The error in the component from a non-ok response shows "Confirm failed. Please try again." — not "Embedding failed"
  timestamp: 2026-03-15

- hypothesis: embedStatus is set to "error" by the catch block in handleConfirm
  evidence: The catch path sets component-level `error` state with "Confirm error: ...", not embedStatus. The "Embedding failed" text is rendered only when embedStatus === "error".
  timestamp: 2026-03-15

## Evidence

- timestamp: 2026-03-15
  checked: backend/services/material_service.py lines 91-105
  found: |
    confirm_material_week returns embed_status based on EMBED_FUNCTION_NAME env var alone,
    NOT on whether the lambda_client.invoke() call succeeds. If EMBED_FUNCTION_NAME is set
    but invoke throws, the except block silently passes AND update_material_embed_status is
    never called (it's inside the try). The DynamoDB record remains embed_status="pending".
    The function then returns embed_status="processing" (because EMBED_FUNCTION_NAME is truthy).
  implication: |
    The confirm API returns embed_status="processing" even when Lambda failed to fire.
    DynamoDB record stays "pending". Frontend starts polling.

- timestamp: 2026-03-15
  checked: frontend/components/MaterialUpload.tsx lines 117-173
  found: |
    On confirm response, initialStatus = confirmData.embed_status ?? "processing".
    If initialStatus === "processing", polling starts.
    First poll (after 4 seconds) fetches /status. The DynamoDB record still has embed_status="pending"
    (Lambda never updated it). The poll returns status="pending".
    The else-if branch at line 166-171 handles "pending": it treats pending as "Lambda never fired
    (e.g. running locally) — stop polling" and sets embedStatus="error", then clears the row after 3s.
  implication: |
    "Embedding failed" appears after ~4 seconds (first poll), then row clears 3 seconds later.
    This exactly matches the reported symptom.

- timestamp: 2026-03-15
  checked: backend/services/material_service.py lines 99-102
  found: |
    The comment says "Only mark processing if invoke succeeded" but the code structure is wrong:
    update_material_embed_status(material_id, "processing") IS inside the try block (line 100),
    so DynamoDB is NOT updated when invoke throws.
    However the return value on line 104 uses EMBED_FUNCTION_NAME truthiness alone:
    embed_status = "processing" if EMBED_FUNCTION_NAME else "pending"
    This means DynamoDB stays "pending" but the API response says "processing".
  implication: |
    Mismatch between what the API reports (processing) and what is stored in DynamoDB (pending).
    The first poll reveals the truth, triggering the "never fired" error path immediately.

## Resolution

root_cause: |
  In confirm_material_week (backend/services/material_service.py), the return value on line 104
  determines embed_status based solely on whether EMBED_FUNCTION_NAME env var is non-empty:
    embed_status = "processing" if EMBED_FUNCTION_NAME else "pending"

  This is wrong in the error case. When Lambda invocation fails (exception caught and silently
  passed on line 101-102), DynamoDB stays "pending" but the API response says "processing".

  The frontend receives "processing", starts polling after 4 seconds, and gets back "pending" from
  DynamoDB. The polling code treats "pending" as "Lambda never fired — stop polling, show error"
  (frontend/components/MaterialUpload.tsx lines 166-171), sets embedStatus="error", renders
  "Embedding failed", then clears the row after 3 seconds.

  The root cause is specifically that the embed_status returned by the confirm API is not derived
  from what actually happened (did DynamoDB get updated to "processing"?) but from a static
  condition (is EMBED_FUNCTION_NAME set?). These diverge when invoke throws.

  Most likely trigger in the UAT environment: Lambda invocation fails because the Lambda function
  is not deployed in the local/dev environment, or EMBED_FUNCTION_NAME is set to a name that does
  not exist in the AWS account being used.

fix: |
  The confirm_material_week function should return embed_status based on whether the DynamoDB
  update to "processing" actually happened (i.e., whether the try block succeeded), not whether
  EMBED_FUNCTION_NAME is truthy. One correct approach:

  Set a local variable (e.g., invoked = False), set it to True inside the try after both invoke
  and update_material_embed_status succeed, then return "processing" only if invoked is True,
  otherwise return "pending".

  The frontend polling code that treats "pending" as an error should remain as-is — it is correct
  behavior for truly local-dev cases where no Lambda is configured.

verification: not applied (find_root_cause_only mode)
files_changed: []
