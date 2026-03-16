# Phase 5: Quiz Generator - Research

**Researched:** 2026-03-16
**Domain:** RAG-based quiz generation — FastAPI backend service, Bedrock structured JSON generation, S3 Vectors retrieval, Next.js multi-screen quiz UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Quiz Flow**
- Questions presented one at a time (step-through), not a scrollable form
- Header shows progress: "Question N of M"
- Navigation: Prev / Next buttons
- After the last question: results screen showing score (X/N correct) + ability to review each question with the correct answer highlighted
- Results screen has a "New quiz" button that returns to the scope/generate screen without leaving the tab

**Answer Feedback**
- Feedback is immediate — as soon as the user selects an option, correct/incorrect is revealed and the explanation is shown
- Answers are locked on selection — no confirm button, no changing after selecting
- Explanation includes a clickable citation link in the same format as TutorChat: `filename — Week N: Topic Label` opens the source file in a new tab via presigned S3 URL
- Incorrect answers are visually marked (e.g. ✘); correct answer is highlighted (e.g. ✔)

**Scope & Size Controls**
- Quiz tab shows a scope configuration screen before generating:
  - Week dropdown: "All weeks" + "Week N: Topic" entries (same data as TutorChat week filter, drawn from weekMap)
  - Question count: segmented control with options 5 / 10 / 15; default is 5
  - Generate Quiz button
- If the selected week has no embedded materials: button is disabled with an inline message ("No materials embedded for Week N")
- Generate button is disabled while generation is in progress (same pattern as TutorChat Send button)

**Generation UX**
- While generating: centered spinner + "Generating your quiz..." message
- If generation fails (Bedrock error / timeout): error message + Retry button that re-submits the same scope
- Generate button is disabled during generation to prevent double-submission

**Scope Screen Layout**
- Week dropdown on top, 5/10/15 segmented control below, Generate button at bottom

**Step-through Question Layout**
- Question text, then four labeled options (A/B/C/D), then feedback expands below selected option after click
- Citation in explanation follows exact tutor format: `filename — Week N: Topic Label` as a clickable link

### Claude's Discretion
- Exact question card styling (border, shadow, spacing)
- Score screen visual design (color for correct/incorrect counts)
- Exact system prompt wording for quiz generation
- How to handle the edge case where Bedrock returns fewer questions than requested
- Animation for the correct/incorrect reveal

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUIZ-01 | User can generate a multiple-choice quiz scoped to a selected unit/week | `retrieve_chunks()` already supports `week_number` filter via S3 Vectors `$and` expression; quiz_service reuses this exactly |
| QUIZ-02 | User can generate a multiple-choice quiz spanning all uploaded course materials | Pass `week_number=None` to `retrieve_chunks()` — same code path as QUIZ-01 with filter omitted |
| QUIZ-03 | Each quiz answer includes an explanation citing the source material it was drawn from | Bedrock generates explanation field per question in JSON output; `build_citations()` already maps material_id → filename + presigned URL; quiz service composes both |
</phase_requirements>

---

## Summary

Phase 5 adds a quiz generator on top of the already-complete RAG infrastructure. The retrieval pipeline (`embed_text`, `retrieve_chunks`, `build_citations`) from Phase 4 is reused unchanged. The only new backend work is a `quiz_service.py` that formats a different Bedrock prompt requesting structured JSON (array of question objects with choices, correct_index, explanation, material_id) and a thin `/quiz/generate` router endpoint.

The frontend is a new `QuizTab.tsx` component that manages three internal view states: scope/config screen, quiz step-through screen, and results/review screen. This three-state machine is the primary complexity of the phase. All state is local to the component — no new API calls beyond the single generate call, no backend state for quiz sessions.

The Lambda 30-second timeout is the binding constraint on the backend. Retrieving a higher `top_k` (to cover more candidate chunks for 10–15 question quizzes) plus generating structured JSON for up to 15 questions through Bedrock must complete within ~25 seconds (Bedrock client's `read_timeout`). Based on Phase 4 tutor patterns, a single Bedrock `converse` call for 15 questions should comfortably fit inside that window.

**Primary recommendation:** Implement `quiz_service.generate_quiz()` following the exact shape of `tutor_service.ask()` — embed query, retrieve chunks, call Bedrock with a JSON-schema prompt, parse response, build citations — then build `QuizTab.tsx` as a three-state component using the same week dropdown and `apiFetch` patterns from `TutorChat`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI + Pydantic | Already installed | Quiz router + request/response models | Matches all existing routers |
| boto3 (bedrock-runtime) | Already installed (>=1.39.5) | Bedrock `converse` call for quiz JSON generation | Same client as tutor_service |
| boto3 (s3vectors) | Already installed (>=1.39.5) | Vector retrieval via `query_vectors` | Same lazy `_get_s3v()` pattern |
| React (Next.js) | Already installed | QuizTab component — three-state UI | Already in use |
| Tailwind CSS | Already installed | Styling consistent with rest of dashboard | Already in use |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` (stdlib) | stdlib | Parse Bedrock's JSON response for quiz questions | Strip markdown fences, parse, validate |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single Bedrock call for all questions | Iterative per-question calls | Per-question calls would multiply latency and hit 30s limit; batch is required |
| Storing quiz sessions in DynamoDB | All state client-side | Quiz sessions are ephemeral; no requirement for persistence or history; client state is simpler and avoids new infra |

**Installation:** No new dependencies. All required libraries are already present.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── services/
│   └── quiz_service.py      # New: generate_quiz() — RAG + Bedrock + citations
├── routers/
│   └── quiz.py              # New: POST /quiz/generate router
└── app.py                   # Edit: include quiz router

frontend/
└── components/
    └── QuizTab.tsx           # New: three-state quiz UI component

frontend/app/dashboard/
└── page.tsx                  # Edit: activate quiz tab, render <QuizTab weekMap={weekMap} />
```

### Pattern 1: Quiz Service (mirrors tutor_service.ask)

**What:** `generate_quiz(user_id, week_number, count)` embeds a generic query, retrieves top-K chunks, calls Bedrock with a structured JSON prompt, parses the response, resolves citations per question.

**When to use:** Called by the quiz router. No session state; returns the complete quiz in one response.

**Example:**
```python
# Mirrors tutor_service.py structure exactly
def generate_quiz(
    user_id: str,
    week_number: int | None,
    count: int,  # 5, 10, or 15
) -> dict:
    """Returns {"questions": [QuestionDict, ...]}"""
    query_embedding = embed_text("key concepts definitions")
    # top_k must be >= count to have enough source material
    chunks = retrieve_chunks(user_id, query_embedding, week_number=week_number, top_k=max(count * 2, 10))

    if not chunks:
        return {"questions": []}  # frontend shows "no materials" state

    questions_raw = generate_questions(chunks, count)  # Bedrock call
    # Resolve citation per question from material_id in chunk metadata
    questions = attach_citations(questions_raw, user_id)
    return {"questions": questions}
```

### Pattern 2: Bedrock Structured JSON Prompt for Quiz

**What:** Send retrieved chunks as context, ask Bedrock to return ONLY a JSON array of question objects. Strip markdown fences before parsing (same as `parse_syllabus_with_bedrock`).

**Example:**
```python
QUIZ_SCHEMA = """[
  {
    "question": "string",
    "choices": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_index": 0,
    "explanation": "string",
    "material_id": "string"
  }
]"""

# System prompt instructs model to return ONLY JSON — no markdown, no preamble
# User message includes context chunks + count requirement
# Response parsing:
raw = response["output"]["message"]["content"][0]["text"].strip()
if raw.startswith("```"):
    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
questions = json.loads(raw)  # list of dicts
```

### Pattern 3: Quiz Router (mirrors tutor.py)

**What:** Single POST endpoint `/quiz/generate`. Receives `week_number` (optional int), `count` (int). Returns `{"questions": [...]}`.

**Example:**
```python
# Source: existing tutor.py pattern
router = APIRouter(prefix="/quiz", tags=["quiz"])

class QuizRequest(BaseModel):
    week_number: int | None = None
    count: int = 5  # 5, 10, or 15

@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(req: QuizRequest, user_id: str = Depends(get_current_user)):
    try:
        result = quiz_service.generate_quiz(
            user_id=user_id,
            week_number=req.week_number,
            count=req.count,
        )
        return QuizResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 4: QuizTab Three-State Machine

**What:** `QuizTab` manages three mutually exclusive views with a single `view` state variable: `"scope"` | `"quiz"` | `"results"`.

**When to use:** Required by the locked decision that all transitions (scope → quiz → results → scope) stay within the same tab without page navigation.

**Example:**
```typescript
type View = "scope" | "quiz" | "results"

export function QuizTab({ weekMap }: QuizTabProps) {
  const [view, setView] = useState<View>("scope")
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [count, setCount] = useState<5 | 10 | 15>(5)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState<(number | null)[]>([])  // index per question
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleGenerate() {
    setLoading(true); setError(null)
    const res = await apiFetch("/api/v1/quiz/generate", {
      method: "POST",
      body: JSON.stringify({ week_number: selectedWeek, count }),
    })
    if (res.ok) {
      const data = await res.json()
      setQuestions(data.questions)
      setAnswers(new Array(data.questions.length).fill(null))
      setCurrentIndex(0)
      setView("quiz")
    } else {
      setError("Quiz generation failed. Please try again.")
    }
    setLoading(false)
  }
  // ...
}
```

### Pattern 5: Citation Resolution per Question

**What:** The quiz service must attach a citation object to each question (not just the overall response), because each question has its own `material_id` from Bedrock's output.

**Example:**
```python
def attach_citations(questions_raw: list[dict], user_id: str) -> list[dict]:
    """For each question, look up material_id → filename + presigned URL."""
    result = []
    url_cache: dict[str, dict] = {}
    for q in questions_raw:
        mid = q.get("material_id")
        if mid and mid not in url_cache:
            item = get_material(mid, user_id)
            if item:
                url_cache[mid] = {
                    "filename": item.get("filename", mid),
                    "week_number": item.get("week_number"),
                    "url": get_presigned_url(mid, user_id),
                }
        q["citation"] = url_cache.get(mid)
        result.append(q)
    return result
```

### Anti-Patterns to Avoid

- **Generating questions one-at-a-time via multiple Bedrock calls:** Each call adds ~2–5 seconds; 15 questions would blow the 30s Lambda timeout. One call for all questions.
- **Storing quiz session in DynamoDB or backend state:** No requirement for persistence. All quiz state lives in React component state.
- **Passing all chunk text to Bedrock without truncation:** S3 Vectors metadata already truncates `source_text` to 500 chars per chunk. Use these truncated texts as context — they fit easily within Bedrock's context window.
- **Using a separate top_k per question:** Retrieve all chunks once with a unified query embedding (e.g. "key concepts"), then pass all chunks as the context block for all N questions in one Bedrock call.
- **Forgetting to handle "0 questions returned":** Bedrock may return fewer than `count` questions if context is thin. The frontend must render whatever count actually came back, not crash on index-out-of-bounds.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector retrieval with week filter | Custom SQL/filter logic | `retrieve_chunks()` from tutor_service (reuse directly) | Already handles S3 Vectors filter syntax, top_k, metadata return |
| S3 presigned URLs for citations | Custom S3 URL builder | `get_presigned_url()` from material_service | Already accounts for user_id scoping and bucket path |
| Bedrock JSON parse with fence stripping | Custom regex | Pattern from `parse_syllabus_with_bedrock` in bedrock_service.py | Already handles ```` ``` ```` prefix/suffix stripping |
| Auth token extraction | Custom middleware | `get_current_user` dependency from middleware/auth.py | Already tested, handles 401/403 correctly |
| API calls with auth header | Custom fetch wrapper | `apiFetch` from lib/api.ts | Auto-injects Bearer token from localStorage |
| Week dropdown UI | New select component | Copy week dropdown from TutorChat.tsx | Identical data shape (weekMap.weeks), identical styling needed |

**Key insight:** This phase is almost entirely assembly of existing pieces. The only net-new logic is the quiz generation prompt and the three-state UI machine.

---

## Common Pitfalls

### Pitfall 1: Lambda Timeout on Large Quiz Requests

**What goes wrong:** Requesting 15 questions with top_k=30 chunks — Bedrock processes more context and may push total time over 25s, hitting the client read_timeout, then Lambda's 30s hard limit.

**Why it happens:** Bedrock inference time scales with both context length and output length. 15 questions with explanations is ~3–4x the output tokens of the tutor chat.

**How to avoid:** Set `top_k = min(count * 2, 20)` — cap at 20 chunks regardless of count. Also set a concise system prompt (no essays in explanations). The existing `BEDROCK_READ_TIMEOUT_S = 25` will surface timeouts as exceptions that the router converts to HTTP 500 with the retry UI.

**Warning signs:** Generation succeeds for 5 questions but times out for 15.

### Pitfall 2: Bedrock Returns Malformed or Partial JSON

**What goes wrong:** Bedrock returns a valid partial JSON array or adds commentary outside the JSON block, causing `json.loads` to raise `JSONDecodeError`.

**Why it happens:** Instruction-following can degrade when context is long. The model may truncate its own output or add a trailing sentence.

**How to avoid:** System prompt must be explicit: "Respond with ONLY the JSON array. No explanation. No markdown code fences. No text before or after the array." Also wrap `json.loads` in a try/except that raises an HTTPException with a user-friendly message (triggers the frontend Retry button).

**Warning signs:** Works in testing with short context, fails in production with 10+ chunks.

### Pitfall 3: material_id in Bedrock Output Doesn't Match Actual material_ids

**What goes wrong:** Bedrock invents a `material_id` rather than copying it faithfully from the context, so `get_material(mid, user_id)` returns None and citation is null.

**Why it happens:** The model treats `material_id` as a text field and may paraphrase or truncate it.

**How to avoid:** In the context block passed to Bedrock, label each chunk with its exact `material_id` in a machine-readable way: `[material_id: {mid}]`. Prompt: "The material_id in each question MUST be copied exactly from the [material_id: ...] tag in the source chunk."

**Warning signs:** `citation` is always null in quiz responses despite materials being embedded.

### Pitfall 4: "No Materials" State for Selected Week

**What goes wrong:** User selects a week, hits Generate, gets back an empty questions array — no visible explanation of why.

**Why it happens:** `retrieve_chunks()` returns `[]` if no vectors are stored for that week (not yet embedded, or no materials assigned to it).

**How to avoid:** On the scope screen, check `materials` prop (available from parent dashboard) to determine if the selected week has at least one `embed_status === "ready"` material. Disable the Generate button with an inline message. This is a locked decision from CONTEXT.md.

**Warning signs:** Empty quiz screen with no error message.

### Pitfall 5: IAM — No New Permissions Needed (but verify)

**What goes wrong:** Assuming new IAM permissions are needed for quiz, adding them, then finding conflicts or redundancy.

**Why it happens:** `SylliFunction` already has `s3vectors:QueryVectors`, `s3vectors:GetVectors`, and `bedrock:InvokeModel`. Quiz generation uses exactly these three — no new permissions required.

**How to avoid:** Do NOT add new IAM statements. Reuse existing permissions. CONTEXT.md confirms: "No new env vars needed — `VECTOR_BUCKET_NAME`, `VECTOR_INDEX_NAME`, `MATERIALS_TABLE` already set."

---

## Code Examples

Verified patterns from existing source files in this codebase:

### S3 Vectors Week-Scoped Retrieval (reuse unchanged)

```python
# Source: backend/services/tutor_service.py — retrieve_chunks()
# For week-scoped quiz (QUIZ-01):
filter_expr = {"$and": [
    {"user_id": {"$eq": user_id}},
    {"week_number": {"$eq": week_number}},
]}
# For all-materials quiz (QUIZ-02):
filter_expr = {"user_id": {"$eq": user_id}}

response = s3v.query_vectors(
    vectorBucketName=VECTOR_BUCKET_NAME,
    indexName=VECTOR_INDEX_NAME,
    topK=top_k,
    queryVector={"float32": query_embedding},
    filter=filter_expr,
    returnMetadata=True,
    returnDistance=False,
)
chunks = response.get("vectors", [])
```

### Bedrock converse Call (reuse pattern)

```python
# Source: backend/services/tutor_service.py — generate_answer()
response = bedrock.converse(
    modelId=MODEL_ID,  # "us.anthropic.claude-sonnet-4-20250514-v1:0"
    system=[{"text": QUIZ_SYSTEM_PROMPT}],
    messages=[{
        "role": "user",
        "content": [{"text": f"Context:\n{context_block}\n\nGenerate {count} quiz questions."}],
    }],
)
raw_text = response["output"]["message"]["content"][0]["text"]
```

### JSON Fence Stripping (reuse pattern)

```python
# Source: backend/services/bedrock_service.py — parse_syllabus_with_bedrock()
stripped = raw_text.strip()
if stripped.startswith("```"):
    stripped = stripped.split("\n", 1)[-1]
    stripped = stripped.rsplit("```", 1)[0]
questions = json.loads(stripped)
```

### Router Registration (app.py edit)

```python
# Source: backend/app.py — add after existing imports and include_router calls
from routers import quiz
app.include_router(quiz.router, prefix="/api/v1")
```

### Week Dropdown (reuse from TutorChat)

```typescript
// Source: frontend/components/TutorChat.tsx
<select
  value={selectedWeek === null ? "" : String(selectedWeek)}
  onChange={(e) => setSelectedWeek(e.target.value === "" ? null : parseInt(e.target.value, 10))}
  className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded px-2 py-1 focus:outline-none focus:border-gray-500"
>
  <option value="">All weeks</option>
  {weekMap.weeks.map((w) => (
    <option key={w.week} value={String(w.week)}>
      Week {w.week}: {w.topic}
    </option>
  ))}
</select>
```

### Dashboard Quiz Tab Activation (page.tsx edit)

```typescript
// Source: frontend/app/dashboard/page.tsx — current disabled quiz tab
// BEFORE:
onClick={() => tab !== "quiz" && setActiveTab(tab)}
disabled={tab === "quiz"}
// {tab === "quiz" ? "Quiz (coming soon)" : ...}

// AFTER:
onClick={() => setActiveTab(tab)}
disabled={false}
// {tab.charAt(0).toUpperCase() + tab.slice(1)}

// Also add QuizTab import and render:
{activeTab === "quiz" && <QuizTab weekMap={weekMap} materials={materials} />}
```

### Citation Display (reuse TutorChat pattern)

```typescript
// Source: frontend/components/TutorChat.tsx — citation rendering
const weekEntry = weekMap.weeks.find((w) => w.week === citation.week_number)
const label = weekEntry ? `Week ${citation.week_number}: ${weekEntry.topic}` : `Week ${citation.week_number}`
const display = `${citation.filename} — ${label}`
// Render as <a href={citation.url} target="_blank">
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bedrock InvokeModel (raw JSON) | Bedrock converse (messages API) | Phase 1 | Quiz must use `converse`, not `invoke_model` — `invoke_model` is only used for embeddings |
| Per-question retrieval | Single batch retrieval + one Bedrock call | This phase design | Keeps total latency under 25s |

**Deprecated/outdated:**
- `bedrock.invoke_model` for chat: Used only for `embed_text` (Titan embeddings). Claude generation always uses `bedrock.converse`.

---

## Open Questions

1. **Exact top_k for quiz retrieval**
   - What we know: tutor uses `top_k=5` for single-answer generation; quiz needs enough material to generate 5–15 distinct questions
   - What's unclear: Whether 20 chunks (cap proposed above) is sufficient for 15 varied questions without redundancy
   - Recommendation: Default to `top_k = min(count * 2, 20)`. If quiz quality is poor (repetitive questions), increase to `min(count * 3, 30)` — adjust via Claude's discretion on system prompt.

2. **How to handle Bedrock returning fewer questions than requested**
   - What we know: This is explicitly marked as Claude's Discretion
   - What's unclear: Whether to pad, re-request, or just show what came back
   - Recommendation: Show whatever count came back. Update the progress header to reflect actual count ("Question 1 of 8" if 8 returned instead of 10). Do not re-request — that doubles latency risk.

3. **Query embedding text for quiz retrieval**
   - What we know: The tutor uses the user's actual question as the embedding query; for quiz generation there's no user question
   - What's unclear: Whether a generic phrase like "key concepts and definitions" produces useful retrieval diversity
   - Recommendation: Use a broad phrase like `"key concepts, definitions, and important topics"` as the embedding input. This is not user-visible; it just seeds the vector search. Claude's discretion.

---

## Sources

### Primary (HIGH confidence)

All findings are verified directly against source files in this repository. No external sources needed — the implementation is a composition of already-proven patterns.

- `backend/services/tutor_service.py` — `retrieve_chunks()`, `build_citations()`, `generate_answer()` patterns reused directly
- `backend/services/bedrock_service.py` — `converse` call shape, JSON fence stripping, MODEL_ID, retry config
- `backend/services/embedding_service.py` — `embed_text()`, `_get_s3v()`, lazy init pattern
- `backend/routers/tutor.py` — Router shape: Pydantic models, `Depends(get_current_user)`, try/except → HTTPException
- `backend/routers/materials.py` — Additional router pattern reference
- `backend/middleware/auth.py` — `get_current_user` dependency signature
- `backend/app.py` — `include_router` registration pattern
- `template.yaml` — Existing IAM permissions (confirms no new policies needed), Lambda 30s timeout constraint
- `frontend/components/TutorChat.tsx` — Week dropdown, `apiFetch` call shape, citation rendering
- `frontend/app/dashboard/page.tsx` — Tab system, quiz tab current state (disabled), weekMap prop flow
- `frontend/lib/api.ts` — `apiFetch` signature
- `.planning/config.json` — `nyquist_validation: false` (skipped Validation Architecture section)

### Secondary (MEDIUM confidence)

- None required — all critical patterns verified from live codebase.

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and proven in phases 3–4
- Architecture: HIGH — all patterns are direct adaptations of existing, working code in this codebase
- Pitfalls: HIGH — Lambda timeout and Bedrock JSON parsing pitfalls are observed from existing services (bedrock_service.py already strips fences); material_id hallucination is a well-known structured-output risk

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack; nothing new to install)
