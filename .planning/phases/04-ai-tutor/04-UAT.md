---
status: complete
phase: 04-ai-tutor
source: 04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md
started: 2026-03-16T21:00:00Z
updated: 2026-03-16T22:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Chat — ask a question and get an answer
expected: Open the Tutor tab. Type a question about your course content and press Enter or click Send. The AI responds with an answer drawn from your uploaded materials — not a generic reply. A "Sources:" section appears below the answer listing at least one citation in the format "filename — Week N: Topic".
result: pass

### 2. Every response includes at least one citation
expected: After receiving a response, check the Sources block below the answer. It should show one or more entries formatted as "filename — Week N: Topic Label". No response should lack a Sources block when materials were found.
result: pass

### 3. Week filter scopes retrieval
expected: In the Tutor tab, open the week filter dropdown. It should list "All weeks" plus one entry per week from your syllabus. Select a specific week, then ask a question. The citations in the response should only reference materials from that week.
result: pass

### 4. Citation links open source files
expected: After receiving a response with a Sources block, click one of the citation links. A new browser tab should open showing the original source file (PDF or PPTX).
result: pass

### 5. Typing indicator while waiting
expected: Submit a question and immediately watch the chat area. A typing indicator (three animated bouncing dots) should appear while the response is loading. The Send button should be disabled during this time.
result: pass

### 6. No-content guard — unrelated question
expected: Ask a question that has no plausible match in your uploaded materials (e.g. "What is the recipe for chocolate cake?"). The AI should return a helpful message indicating it couldn't find relevant content — not a hallucinated answer.
result: pass

### 7. Tab navigation — Library | Tutor | Quiz
expected: The dashboard shows three tabs: Library, Tutor, and Quiz. Library is the active default. Clicking Tutor shows the chat interface. Clicking Quiz shows a disabled/coming-soon state. Switching tabs does not lose current chat messages.
result: pass

### 8. Collapsed syllabus section
expected: When a syllabus is already uploaded, the top of the dashboard shows a compact "Replace syllabus" button instead of the full upload form. Clicking it reveals the upload form again.
result: pass

## Summary

total: 8
passed: 8
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Failed-upload files can be deleted from the library"
  status: failed
  reason: "User reported: old files that failed to upload are still there and the delete button isn't working"
  severity: major
  test: 0
  root_cause: "handleDeleteMaterial in MaterialLibrary.tsx discards the apiFetch Response — no res.ok check. Any API error (404/500) is silently swallowed, then onRefresh() is called unawaited causing a race where the list re-fetches before the DELETE commits, repopulating the deleted item."
  artifacts:
    - path: "frontend/components/MaterialLibrary.tsx"
      issue: "handleDeleteMaterial (lines 38-41): res from apiFetch not checked; onRefresh() called without await; delete button has no disabled/loading state during in-flight request"
  missing:
    - "Check res.ok before calling onRefresh(); surface error to user if !res.ok"
    - "Await onRefresh() after confirmed successful DELETE"
    - "Disable delete button during in-flight request to prevent double-clicks"
  debug_session: ".planning/debug/library-delete-button-not-working.md"
