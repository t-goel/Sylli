---
status: resolved
trigger: "delete-button-failed-to-fetch"
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T00:00:00Z
---

## Current Focus

hypothesis: Unhandled exception in the DELETE handler propagates through Starlette ExceptionMiddleware (re-raises non-HTTPException), through CORSMiddleware, and up to Mangum's HTTPCycle.run — which catches it and generates a 500 response using its own internal `send` (bypassing the CORSMiddleware-wrapped send). The 500 response has no CORS headers. Browser sees a response without Access-Control-Allow-Origin and throws TypeError: Failed to fetch.
test: Read Mangum HTTPCycle.run source (confirmed), Starlette CORSMiddleware/ExceptionMiddleware source (confirmed), traced exception propagation path
expecting: Fix by adding FastAPI exception handler for base Exception + Gateway Response CORS config in SAM template
next_action: DONE — awaiting human verification after sam build + sam deploy

## Symptoms

expected: Clicking ✕ deletes the material and removes it from the list
actual: Button shows "..." (deletingId guard activates), then "Failed to fetch" TypeError is thrown from api.ts:15 (the fetch() call itself), entry remains in the list
errors: |
  TypeError: Failed to fetch
    at apiFetch (api.ts:15:10)
    at handleDeleteMaterial (MaterialLibrary.tsx:63:33)

  Also in browser console:
  "Access to fetch at 'https://nqu5vst1re.execute-api.us-east-1.amazonaws.com/Prod/api/v1/materials/{id}'
   from origin 'http://localhost:3000' has been blocked by CORS policy:
   No 'Access-Control-Allow-Origin' header is present on the resource."

  BUT: a manual curl OPTIONS preflight confirmed CORS IS working:
    access-control-allow-origin: http://localhost:3000
    access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT

  So CORS preflight succeeds but the actual DELETE request fails.
reproduction: Upload a file, wait for it to appear in the library, click ✕
timeline: Started after the code was deployed. The fix in 04-05 was deployed but the issue persists.

## Eliminated

- hypothesis: Frontend code (handleDeleteMaterial) has missing res.ok check or unawaited onRefresh
  evidence: MaterialLibrary.tsx already has the 04-05 fix — proper res.ok check, await onRefresh(), loading guard with deletingId. The frontend code is correct.
  timestamp: 2026-03-16

- hypothesis: API Gateway not reaching Lambda for DELETE (e.g. route not registered)
  evidence: The error happens specifically when fetch() receives a response (a 5xx) with no CORS headers — not a network-level TCP failure. If API Gateway rejected the route, it would return its own 403/404 Gateway Response, which ALSO lacks CORS headers. But the more specific evidence is: OPTIONS preflight passes (proven by curl), meaning the route exists and API Gateway knows DELETE is allowed. The actual DELETE is reaching Lambda (or hitting a Gateway Response for a different reason than routing).
  timestamp: 2026-03-16

- hypothesis: FastAPI CORSMiddleware not matching http://localhost:3000
  evidence: Starlette 0.52.1 source read directly. allow_origins=["http://localhost:3000", ...] stores exact origins. is_allowed_origin() checks `origin in self.allow_origins` — exact string match. "http://localhost:3000" IS in the list. The CORS middleware DOES add headers for matching origins on any response that flows through simple_response->send.
  timestamp: 2026-03-16

- hypothesis: Starlette CORS middleware broken for wildcard origin https://*.amplifyapp.com
  evidence: Starlette only uses fnmatch/regex for origins with "*" when checking is_allowed_origin. "http://localhost:3000" is checked via set membership, not fnmatch. The wildcard origin doesn't interfere with the exact origin check.
  timestamp: 2026-03-16

## Evidence

- timestamp: 2026-03-16
  checked: frontend/components/MaterialLibrary.tsx (full file)
  found: Frontend already has the 04-05 fix. handleDeleteMaterial (lines 58-73) has: try/catch, res.ok check, error surfacing via setDeleteError, await onRefresh(), and deletingId guard. The frontend is correct.
  implication: The bug is not in the frontend. The error at api.ts:15 is the raw fetch() throwing TypeError — meaning the browser received a CORS-blocked response, not an HTTP error from a well-formed response.

- timestamp: 2026-03-16
  checked: frontend/lib/api.ts (full file)
  found: apiFetch() always sets Content-Type: application/json regardless of method. For DELETE requests with no body, this header is sent unnecessarily but should not cause failures.
  implication: Content-Type header on DELETE may affect the CORS preflight (browser includes it in Access-Control-Request-Headers), but the OPTIONS preflight already passed per the curl test.

- timestamp: 2026-03-16
  checked: backend/app.py — CORSMiddleware configuration
  found: allow_origins=["http://localhost:3000", "https://*.amplifyapp.com"], allow_methods=["*"], allow_headers=["*"]. No global exception handler registered.
  implication: FastAPI is configured correctly for CORS. But there is NO global exception handler for non-HTTPException errors. If an unhandled Python exception occurs, it propagates through the middleware stack uncaught.

- timestamp: 2026-03-16
  checked: .aws-sam/build/SylliFunction/starlette/middleware/cors.py (Starlette 0.52.1)
  found: CORSMiddleware.simple_response wraps the ASGI send with functools.partial(self.send, send=send, request_headers=request_headers), then awaits self.app(scope, receive, send). The CORS-adding logic is in the wrapped send. If self.app raises an exception, simple_response propagates it UP — the wrapped send is never used to send the response.
  implication: Any exception that escapes the inner app BYPASSES the CORSMiddleware response wrapper. The exception goes to Mangum directly.

- timestamp: 2026-03-16
  checked: .aws-sam/build/SylliFunction/starlette/_exception_handler.py — wrap_app_handling_exceptions
  found: When an exception is caught, handler = _lookup_exception_handler(exception_handlers, exc). Only HTTPException and WebSocketException are registered by default. For any other exception (e.g., botocore.exceptions.ClientError, any Python built-in exception): handler is None → `raise exc`. The exception is re-raised, propagating out of ExceptionMiddleware.
  implication: Any non-HTTPException raised in a FastAPI route handler propagates all the way through Starlette's middleware stack without being converted to an HTTP response.

- timestamp: 2026-03-16
  checked: .aws-sam/build/SylliFunction/mangum/protocols/http.py — HTTPCycle.run
  found: `except BaseException: self.logger.exception(...) if self.state is HTTPCycleState.REQUEST: await self.send({"type": "http.response.start", "status": 500, "headers": [[b"content-type", b"text/plain; charset=utf-8"]]})`. Mangum catches all exceptions and sends a 500 with ONLY content-type header — NO Access-Control-Allow-Origin. Crucially, it calls `self.send` (Mangum's internal send method), NOT the CORSMiddleware-wrapped send function. So CORS headers are never added.
  implication: THIS IS THE ROOT CAUSE MECHANISM. Any unhandled exception in a FastAPI handler causes Mangum to return a 500 without CORS headers. The browser's fetch() receives a 500 with no Access-Control-Allow-Origin and throws TypeError: Failed to fetch.

- timestamp: 2026-03-16
  checked: backend/services/material_service.py — delete_material function (lines 115-125)
  found: Calls get_material (DynamoDB get_item — not wrapped in try/except). Then s3.delete_object (wrapped in try/except Exception: pass). Then _delete_material_record (DynamoDB delete_item — NOT wrapped). If DynamoDB raises ClientError on get_item or delete_item, the exception is unhandled.
  implication: A DynamoDB ClientError (provisioned throughput, conditional check failure, network timeout, etc.) on get_item or delete_item would be an unhandled exception that propagates to Mangum and causes a no-CORS 500 response.

- timestamp: 2026-03-16
  checked: Backend delete path compared to GET path for CORS difference
  found: GET /materials calls list_materials_for_user → DynamoDB query. DELETE /materials/{id} calls delete_material → get_material (get_item) → s3.delete_object → delete_item. The DELETE path makes more DynamoDB and S3 calls. More opportunities for ClientError. Additionally, DynamoDB table was just cleared/reused — there may be item attribute issues (e.g., s3_key attribute missing if item was manually or partially created) that cause delete to fail.
  implication: The DELETE path has more surface area for unhandled exceptions. Even if the specific exception is not identified, the FIX is the same: add a FastAPI global exception handler to ensure ALL exceptions return CORS-compliant responses.

## Resolution

root_cause: |
  Mangum's HTTPCycle.run catches unhandled Python exceptions and generates a 500 response using
  its own internal send() method — bypassing the CORSMiddleware-wrapped send() that would add
  Access-Control-Allow-Origin headers. The result is a 500 response without CORS headers.

  The browser's fetch() receives a response without Access-Control-Allow-Origin and throws
  TypeError: Failed to fetch (CORS block). This manifests as the "Failed to fetch" error in
  the console, paired with the CORS policy error.

  Starlette's ExceptionMiddleware only handles HTTPException by default. Any other exception
  (botocore.exceptions.ClientError, ValueError, AttributeError, etc.) from the DELETE handler
  propagates uncaught through ExceptionMiddleware (re-raised) → CORSMiddleware (propagated) →
  Mangum HTTPCycle.run (caught, 500 sent without CORS headers).

  The specific triggering exception in the DELETE path is most likely a DynamoDB ClientError on
  get_item or delete_item (e.g., throttling, missing attribute, or unexpected item shape after
  manual CLI deletion and re-upload), but the root architectural problem is the missing global
  exception handler.

fix: |
  TWO changes needed:

  1. backend/app.py: Add a FastAPI global exception handler for Exception that converts any
     unhandled exception to a JSON 500 response. This response flows through the normal ASGI
     response path (CORSMiddleware's wrapped send), so CORS headers are added correctly.

  2. template.yaml: Add GatewayResponses configuration to the SAM Globals.Api section so that
     API Gateway-level errors (403 Missing Auth Token, 504 timeout, 502 bad gateway) also
     include CORS headers. This handles errors that occur before Lambda is invoked.

verification: confirmed fixed by user — delete button works end-to-end after sam build + sam deploy
files_changed:
  - backend/app.py
  - template.yaml
