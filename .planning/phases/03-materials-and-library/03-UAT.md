---
status: diagnosed
phase: 03-materials-and-library
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md]
started: 2026-03-16T05:00:00Z
updated: 2026-03-16T05:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. File Upload with AI Week Suggestion
expected: Go to the dashboard (logged in, syllabus loaded). Select a PDF/PPTX/DOCX. Upload completes within ~10s showing inline row: filename, AI-suggested week + topic, "Confirm" and "Change week" buttons. File input resets.
result: pass

### 2. Change Week Dropdown
expected: Click "Change week". A dropdown appears listing all weeks from the syllabus (e.g. "Week 1: Topic", "Week 2: Topic"...). Select a different week — the week label in the row updates immediately. Dropdown closes when week is selected.
result: pass

### 3. Confirm — Processing Badge
expected: Click "Confirm". The Confirm/Change week buttons disappear and a gray "Processing..." text appears immediately in the upload row.
result: issue
reported: "it just says embedding failed and then disappears"
severity: major

### 4. Embed Pipeline (requires deployed AWS)
expected: After confirming, wait 30–120 seconds. The "Processing..." badge transitions to green "Embedded" text, then the upload row disappears. The file appears in the library under the correct week. Requires EmbedWorkerFunction deployed, sylli-vectors S3 Vectors bucket + index, and Bedrock Titan Embed V2 access.
result: skipped
reason: Blocked by Test 3 issue — embed worker Lambda not firing

### 5. Material Library — All Weeks Shown
expected: Scroll to "Course Materials" on the dashboard. Every week from the syllabus appears as a section header (e.g. "Week 1: Topic"). Weeks with no uploaded materials show "no materials yet" in gray text. Weeks with materials show the file rows.
result: pass

### 6. Click Material to View
expected: Click a confirmed material row in the library. The original file opens in a new browser tab. Clicking the same row again (even 5+ minutes later) should still open the file — each click generates a fresh presigned URL.
result: pass

### 7. Delete Material
expected: Hover over a material row in the library. A small "✕" button appears on the right. Clicking it removes the material from the library immediately (no page reload needed).
result: pass

### 8. Delete While Processing Clears Upload Row
expected: Upload a file, click Confirm (Processing... appears), then delete that material from the library using the ✕ button. Within 4 seconds, the "Processing..." upload row should clear automatically and the file input should become available again.
result: pass

## Summary

total: 8
passed: 6
issues: 1
pending: 0
skipped: 1

## Gaps

- truth: "Click Confirm shows 'Processing...' badge immediately, Confirm/Change week buttons disappear"
  status: failed
  reason: "User reported: it just says embedding failed and then disappears"
  severity: major
  test: 3
  root_cause: "confirm_material_week returns embed_status='processing' based on EMBED_FUNCTION_NAME truthiness, not whether lambda_client.invoke() succeeded. When invoke throws, except block silently passes, DynamoDB stays at 'pending'. Frontend polls 4s later, gets 'pending', treats it as 'Lambda never fired' and shows Embedding failed."
  artifacts:
    - path: "backend/services/material_service.py"
      issue: "embed_status return value on line 104 not tied to actual invoke outcome — set to 'processing' even when lambda invoke throws"
    - path: "frontend/components/MaterialUpload.tsx"
      issue: "lines 166-171: polled status==='pending' treated as error (correct behavior, not a bug)"
  missing:
    - "Track whether invoke+update_material_embed_status succeeded with local boolean"
    - "Return 'processing' only when invoked=True, otherwise return 'pending'"
  debug_session: ".planning/debug/confirm-embedding-failed.md"
