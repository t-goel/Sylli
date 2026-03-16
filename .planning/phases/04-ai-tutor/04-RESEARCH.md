# Phase 4: AI Tutor - Research

**Researched:** 2026-03-16
**Domain:** RAG (Retrieval-Augmented Generation) — AWS S3 Vectors + Bedrock Converse API + FastAPI
**Confidence:** HIGH

## Summary

Phase 4 builds a synchronous RAG chat endpoint on the existing infrastructure. The retrieval side uses S3 Vectors `query_vectors` with metadata filtering (already exercised in Phase 3 for writes), and the generation side extends the existing `bedrock_service.py` `converse` call to accept multi-turn messages plus an injected context block. Both APIs are battle-tested in this codebase; no new AWS services are introduced.

The frontend adds a three-tab layout (Library | Tutor | Quiz) wrapping the existing content, a new `TutorChat.tsx` component with session-local state, a week-filter dropdown derived from the syllabus `week_map`, and a citations block rendered below each AI response. The presigned-URL-on-click pattern from `MaterialLibrary.tsx` is reused verbatim for citation links.

The biggest integration risk is the IAM policy gap: `query_vectors` with `returnMetadata=true` requires **both** `s3vectors:QueryVectors` and `s3vectors:GetVectors` in `template.yaml`. The existing policy only grants `s3vectors:PutVectors` to EmbedWorkerFunction; SylliFunction has no s3vectors permissions at all. Both must be added before the RAG query can work.

**Primary recommendation:** Add `s3vectors:QueryVectors` + `s3vectors:GetVectors` to `SylliFunction` in `template.yaml`, write a `tutor_service.py` that calls `embed_text` + `query_vectors` + `bedrock.converse`, and wire a new `/api/v1/tutor/chat` POST router.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Three-tab layout on the dashboard: **Library | Tutor | Quiz**
- Quiz tab is a placeholder (Phase 5) — visible but disabled or shows "Coming soon"
- Default tab on dashboard load: **Library**
- Syllabus upload section: once uploaded, replaced by compact "Replace syllabus" button that reveals the upload UI on click
- Chat history is session-only (no DynamoDB persistence); last **5 turns** sent as conversation context
- Loading state: animated typing indicator (dots) while waiting for AI response
- Send button disabled while a request is in-flight
- Each AI response ends with a separate **"Sources:" block** below the prose response
- Citation format: `filename — Week N: Topic Label`
- Citations are clickable links — open source file in new tab via presigned S3 URL (same as library material click)
- Chat header includes a **week filter dropdown** populated from syllabus `week_map`
- Default filter: **"All weeks"** (unfiltered)
- RAG retrieval: **top 5 chunks** per query
- Tutor persona: helpful study assistant, concise, grounded in retrieved content, no filler

### Claude's Discretion
- Exact system prompt wording for the tutor persona
- How to handle no relevant chunks found
- Chat bubble styling (user vs AI message)
- Whether to use a `TutorChat.tsx` component or extend existing
- Error handling for failed Bedrock calls (in-chat error vs toast)
- Exact animation style for typing indicator

### Deferred Ideas (OUT OF SCOPE)
- Streaming chat responses (word-by-word) — TUTOR-V2-02
- Week-scoped-only mode — TUTOR-V2-01
- Persistent chat history across sessions
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TUTOR-01 | User can chat with an AI tutor that answers questions using their uploaded course materials | RAG pipeline: embed query via `embed_text()`, retrieve top-5 chunks from S3 Vectors with `user_id` filter, inject chunks as context in Bedrock `converse` call |
| TUTOR-02 | Every AI tutor response cites the specific source file and unit/week it referenced | S3 Vectors metadata stores `material_id`, `week_number`, and `source_text`; response includes citations derived from retrieved chunk metadata; presigned URL generated per citation using existing `/materials/{id}/view` pattern |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| boto3 s3vectors | >=1.39.5 (pinned in requirements.txt) | `query_vectors` for similarity search | Already in project, used in embed worker |
| boto3 bedrock-runtime | same | `converse` for multi-turn generation | Already in `bedrock_service.py` |
| FastAPI + Pydantic | current (in project) | RAG endpoint with typed request/response models | Established pattern across all routers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `services/embedding_service.py` existing | — | `embed_text()` for query embedding, `_get_s3v()` for S3 Vectors client | Reuse directly — no new library needed |
| `services/bedrock_service.py` existing | — | Bedrock client with retry config | Extend for tutor; avoid creating a second client |
| `services/material_service.py` existing | — | `get_presigned_url()` for citation links | Reuse for generating clickable citation URLs |

### No New Dependencies Required
This phase requires zero new pip packages. All infrastructure is in place from Phase 3.

**No installation required** — existing `requirements.txt` covers everything.

---

## Architecture Patterns

### Recommended File Structure (new files only)
```
backend/
├── routers/
│   └── tutor.py           # POST /api/v1/tutor/chat
├── services/
│   └── tutor_service.py   # RAG orchestration: embed → query → generate

frontend/
├── components/
│   └── TutorChat.tsx      # Chat UI with session state, week filter, citations
```

Changes to existing files:
- `backend/app.py` — register tutor router
- `template.yaml` — add s3vectors:QueryVectors + s3vectors:GetVectors to SylliFunction

### Pattern 1: RAG Pipeline in tutor_service.py
**What:** Embed the question, query S3 Vectors with user_id filter (and optionally week_number filter), build a context string from retrieved chunks, call Bedrock converse with system prompt + context + conversation history.
**When to use:** Every `/tutor/chat` request.

```python
# Source: embedding_service.py existing + S3 Vectors boto3 docs
def retrieve_chunks(
    user_id: str,
    query_embedding: list[float],
    week_number: int | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Query S3 Vectors for top-K chunks scoped to user, optionally filtered by week."""
    s3v = _get_s3v()
    filter_expr: dict = {"user_id": {"$eq": user_id}}
    if week_number is not None:
        filter_expr = {"$and": [
            {"user_id": {"$eq": user_id}},
            {"week_number": {"$eq": week_number}},
        ]}
    response = s3v.query_vectors(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=VECTOR_INDEX_NAME,
        topK=top_k,
        queryVector={"float32": query_embedding},
        filter=filter_expr,
        returnMetadata=True,   # requires s3vectors:GetVectors IAM permission
        returnDistance=False,
    )
    return response.get("vectors", [])
```

### Pattern 2: Multi-turn Converse Call
**What:** Pass the last 5 turns of conversation history plus a RAG context block as the first user message or system prompt addendum.
**When to use:** Every generate call.

```python
# Source: AWS Bedrock Converse API docs
# existing bedrock client from bedrock_service.py (reuse, don't create second client)

def generate_answer(
    question: str,
    context_chunks: list[dict],
    history: list[dict],  # [{"role": "user"|"assistant", "content": "..."}]
) -> tuple[str, list[dict]]:
    """Generate an answer grounded in retrieved chunks. Returns (answer_text, citations)."""
    # Build context block from retrieved vectors
    context_lines = []
    for chunk in context_chunks:
        meta = chunk.get("metadata", {})
        context_lines.append(
            f"[Source: {meta.get('material_id', '?')}, "
            f"Week {meta.get('week_number', '?')}]\n"
            f"{meta.get('source_text', '')}"
        )
    context_block = "\n\n---\n\n".join(context_lines)

    # Build messages: history + new question with context injected
    messages = [
        {"role": m["role"], "content": [{"text": m["content"]}]}
        for m in history[-10:]  # last 5 turns = 10 messages (user+assistant pairs)
    ]
    messages.append({
        "role": "user",
        "content": [{"text": f"Context from course materials:\n{context_block}\n\nQuestion: {question}"}],
    })

    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": TUTOR_SYSTEM_PROMPT}],
        messages=messages,
    )
    answer = response["output"]["message"]["content"][0]["text"]
    return answer
```

### Pattern 3: Citation Assembly
**What:** After retrieving chunks, look up each unique `material_id` in DynamoDB to get `filename` and `week_number`, then generate a presigned URL from `material_service.get_presigned_url()`.
**When to use:** On every RAG response that has retrieved chunks.

```python
# Source: dynamo_service.get_material() + material_service.get_presigned_url() (existing)

def build_citations(chunk_vectors: list[dict], user_id: str) -> list[dict]:
    """Deduplicate by material_id and fetch presigned URL + week label per citation."""
    seen = {}
    for v in chunk_vectors:
        meta = v.get("metadata", {})
        mid = meta.get("material_id")
        if mid and mid not in seen:
            item = get_material(mid, user_id)  # dynamo_service.get_material
            if item:
                url = get_presigned_url(mid, user_id)  # material_service
                seen[mid] = {
                    "material_id": mid,
                    "filename": item.get("filename", mid),
                    "week_number": meta.get("week_number"),
                    "url": url,
                }
    return list(seen.values())
```

### Pattern 4: API Request/Response Schema
**What:** Typed Pydantic models for the `/tutor/chat` endpoint.
**When to use:** Router + service boundary.

```python
# Standard FastAPI Pydantic pattern (existing project convention)
from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str          # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []    # last N turns, client manages
    week_number: int | None = None     # None = all weeks

class Citation(BaseModel):
    filename: str
    week_number: int | None
    url: str | None                    # presigned S3 URL

class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
```

### Pattern 5: Tab UI in dashboard/page.tsx
**What:** State-controlled tab bar using a `activeTab` useState, wrapping existing sections in the Library tab.
**When to use:** Restructuring dashboard layout.

```tsx
// Simple state-driven tab, no library needed (existing Tailwind classes)
const [activeTab, setActiveTab] = useState<"library" | "tutor" | "quiz">("library")

// Tab bar
<div className="flex gap-1 mb-6 border-b border-gray-800">
  {(["library", "tutor", "quiz"] as const).map((tab) => (
    <button
      key={tab}
      onClick={() => tab !== "quiz" && setActiveTab(tab)}
      className={`px-4 py-2 text-sm capitalize transition-colors ${
        activeTab === tab
          ? "border-b-2 border-white text-white"
          : tab === "quiz"
          ? "text-gray-600 cursor-not-allowed"
          : "text-gray-400 hover:text-gray-200"
      }`}
      disabled={tab === "quiz"}
    >
      {tab === "quiz" ? "Quiz (coming soon)" : tab.charAt(0).toUpperCase() + tab.slice(1)}
    </button>
  ))}
</div>
```

### Anti-Patterns to Avoid
- **Creating a second Bedrock boto3 client:** `bedrock_service.py` already has one configured with correct retry/timeout settings. Import and reuse it in `tutor_service.py`.
- **Storing chat history server-side:** Decisions lock this to session-only. Keep history in React state on the client.
- **Embedding query inside the router:** Follow established pattern — service raises, router catches as HTTPException.
- **Sending full chunk text in the citation URL:** Citations link to the full file via presigned URL, not to the chunk text. Chunk text is only used for context injection.
- **Forgetting IAM for returnMetadata:** Calling `query_vectors` with `returnMetadata=True` without `s3vectors:GetVectors` will fail with HTTP 403. This is the most likely silent failure during testing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom cosine similarity over stored embeddings | S3 Vectors `query_vectors` | Already storing vectors there from Phase 3 |
| Query embedding | Re-implement embedding | `embedding_service.embed_text()` | Already tested, uses Titan Embed V2 at 1024 dims |
| Presigned URL for citation | Direct S3 URL construction | `material_service.get_presigned_url()` | Already handles auth + expiry; used in MaterialLibrary |
| Chat bubble UI framework | Build custom chat renderer | React state + Tailwind divs | Codebase uses no component library; stay consistent |
| Streaming | SSE/chunked response infrastructure | N/A — deferred to v2 | Mangum + API Gateway 29s limit makes streaming complex; synchronous response within 30s is the v1 contract |

**Key insight:** Every primitive (vector client, Bedrock client, presigned URLs, auth) already exists in Phase 3 services. This phase is primarily orchestration.

---

## Common Pitfalls

### Pitfall 1: Missing s3vectors:GetVectors IAM Permission
**What goes wrong:** `query_vectors` with `returnMetadata=True` returns HTTP 403 at runtime with a confusing "Access Denied" error, even though `s3vectors:QueryVectors` is present.
**Why it happens:** AWS S3 Vectors separates the query operation (finds vector keys) from metadata retrieval (reads metadata payload). Both permissions are required when `returnMetadata=True`.
**How to avoid:** In `template.yaml`, add to SylliFunction's Policies:
```yaml
- Statement:
    - Effect: Allow
      Action:
        - s3vectors:QueryVectors
        - s3vectors:GetVectors
      Resource: "*"
```
**Warning signs:** 403 error from s3vectors client, `chunk.get("metadata", {})` returns empty dicts despite metadata existing.

### Pitfall 2: source_text Truncated at 500 Characters in Metadata
**What goes wrong:** `source_text` stored during Phase 3 embedding is truncated to 500 chars (`chunks[i][:500]` in `embedding_service.py`). Context quality suffers for long conceptual paragraphs.
**Why it happens:** S3 Vectors has a 2 KB filterable metadata size limit per vector; truncation was a deliberate Phase 3 choice.
**How to avoid:** 500 chars is typically 3-5 sentences — sufficient for RAG context. Acknowledge in prompts. If quality is poor, increase truncation limit (check against 2 KB per vector constraint), but don't exceed it.
**Warning signs:** Tutor gives vague answers despite relevant content existing in materials.

### Pitfall 3: Conversation History Role Interleaving
**What goes wrong:** Bedrock Converse API requires strictly alternating user/assistant roles. Sending two consecutive user messages (e.g., if history is malformed) causes a validation error.
**Why it happens:** Client may send history in unexpected order, or history may start with an assistant message.
**How to avoid:** On the backend, validate/normalize the history list before passing to Bedrock: ensure it starts with a user role and alternates. The last message must always be a user message (the current question).
**Warning signs:** Bedrock throws `ValidationException` mentioning message roles.

### Pitfall 4: Lambda 30s Timeout Under Load
**What goes wrong:** RAG pipeline has 3 sequential latency sources: embed query (~0.5s), S3 Vectors query (~0.5-2s), Bedrock generation (~5-15s). Under retry conditions this can approach the 30s limit.
**Why it happens:** `bedrock_service.py` sets a 25s read timeout and up to 3 retries. With network issues, 3 retry attempts alone can exceed the Lambda timeout.
**How to avoid:** For the tutor endpoint, consider using max_attempts=2 (not 3) or a shorter read_timeout (20s). The existing `BEDROCK_READ_TIMEOUT_S=25` is fine for single attempts; the risk is retry accumulation.
**Warning signs:** Lambda logs show `Task timed out after 30.XX seconds`; frontend gets a 503/504 from API Gateway.

### Pitfall 5: Week Filter Dropdown Populated Before Syllabus Loads
**What goes wrong:** `TutorChat.tsx` renders the week filter dropdown from `weekMap` prop. If the parent dashboard hasn't finished loading the syllabus yet, the dropdown shows only "All weeks" with no options.
**Why it happens:** Dashboard `useEffect` fetches syllabus asynchronously; weekMap starts null.
**How to avoid:** Accept `weekMap` as a prop from the dashboard (matching the MaterialLibrary pattern). The tab won't be visible until weekMap is loaded anyway, so this is low risk. Ensure TutorChat handles `weekMap === null` gracefully.

### Pitfall 6: No "Ready" Materials Guard
**What goes wrong:** A user asks a question but all their materials have `embed_status !== "ready"`. S3 Vectors returns zero results, and the LLM generates a generic response without grounding.
**Why it happens:** Materials may still be processing when the user first opens the Tutor tab.
**How to avoid:** The "no chunks found" case (decided to be Claude's discretion) should return a clear response like "I couldn't find relevant content in your materials. Make sure your materials have finished processing (check the Library tab)." Check `vectors == []` after query and short-circuit before calling Bedrock.

---

## Code Examples

### Complete RAG Query Call (S3 Vectors)
```python
# Source: https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors/client/query_vectors.html
# Note: returnMetadata=True requires BOTH s3vectors:QueryVectors AND s3vectors:GetVectors in IAM

response = s3v.query_vectors(
    vectorBucketName=VECTOR_BUCKET_NAME,
    indexName=VECTOR_INDEX_NAME,
    topK=5,
    queryVector={"float32": query_embedding},  # list[float], 1024 dims (Titan Embed V2)
    filter={"$and": [
        {"user_id": {"$eq": user_id}},
        # {"week_number": {"$eq": week_number}},  # add when week filter is active
    ]},
    returnMetadata=True,
    returnDistance=False,
)
# Response: {"vectors": [{"key": "mat_id#chunk#0", "metadata": {...}}, ...]}
```

### Multi-turn Bedrock Converse (conversation history)
```python
# Source: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html
# Messages must strictly alternate user/assistant roles; last must be "user"

response = bedrock.converse(
    modelId=MODEL_ID,  # "us.anthropic.claude-sonnet-4-20250514-v1:0"
    system=[{"text": TUTOR_SYSTEM_PROMPT}],
    messages=[
        # history (last 5 turns, 10 messages)
        {"role": "user",      "content": [{"text": "previous question"}]},
        {"role": "assistant", "content": [{"text": "previous answer"}]},
        # current question with injected RAG context
        {"role": "user",      "content": [{"text": f"Context:\n{context_block}\n\nQuestion: {question}"}]},
    ],
)
answer_text = response["output"]["message"]["content"][0]["text"]
```

### IAM Policy Block for template.yaml (SylliFunction)
```yaml
# Add to SylliFunction Policies section
- Statement:
    - Effect: Allow
      Action:
        - s3vectors:QueryVectors
        - s3vectors:GetVectors
      Resource: "*"
```

### Metadata filter — all weeks (user-scoped only)
```python
filter_expr = {"user_id": {"$eq": user_id}}
```

### Metadata filter — specific week
```python
filter_expr = {"$and": [
    {"user_id": {"$eq": user_id}},
    {"week_number": {"$eq": week_number}},
]}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `invoke_model` for text generation | `converse` API | Bedrock ~2024 | Unified message format, cleaner multi-turn, no model-specific JSON marshaling |
| External vector stores (Pinecone, Chroma) | S3 Vectors | 2025 (Phase 3 decision) | AWS-native, no extra service, per-user filter via metadata |
| Streaming via Lambda Function URL | Synchronous response | v1 constraint | Mangum + API Gateway don't support native streaming; deferred to v2 |

**Deprecated/outdated:**
- Bedrock Knowledge Bases: ruled out in REQUIREMENTS.md — no per-user data isolation.
- `invoke_model` for chat: still works but `converse` is the current standard for conversational use cases.

---

## Open Questions

1. **source_text metadata field vs. chunk_index for full text retrieval**
   - What we know: `source_text` stores only 500 chars per chunk. `chunk_index` and `material_id` are stored but the full chunk text is not retrievable without re-downloading the S3 file.
   - What's unclear: Whether 500 chars provides adequate RAG context quality for all material types (dense academic PDFs vs. slide decks).
   - Recommendation: Ship with 500-char source_text. If quality is poor in testing, evaluate increasing the truncation limit (staying under the 2 KB S3 Vectors metadata limit per vector) rather than adding a separate chunk store.

2. **Single-user filter performance vs. $and compound filter**
   - What we know: S3 Vectors evaluates filters in tandem with nearest-neighbor search, not as post-filtering. `$and` compound filters should not be significantly slower than single-key filters.
   - What's unclear: Exact performance characteristics at small data volumes (this is a student tool, not production scale).
   - Recommendation: Use compound `$and` filter for week-scoped queries — correctness over micro-optimization.

3. **Bedrock response hallucination when no chunks are found**
   - What we know: If zero chunks are returned, sending an empty context to Claude may result in a generic response drawing on training data rather than the user's materials.
   - What's unclear: Whether a zero-chunk guard before calling Bedrock is better UX than letting Claude acknowledge the empty context.
   - Recommendation: Short-circuit before calling Bedrock when `vectors == []`. Return a no-content message from the service. This prevents training-data answers from leaking into what should be a course-grounded tutor.

---

## Sources

### Primary (HIGH confidence)
- [S3 Vectors `query_vectors` boto3 docs](https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors/client/query_vectors.html) — method signature, parameters, response structure
- [S3 Vectors Metadata Filtering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-metadata-filtering.html) — filter syntax operators ($eq, $and, $or, $in)
- [S3 Vectors IAM Permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-access-management.html) — GetVectors required for returnMetadata
- [Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html) — multi-turn messages array format
- Existing codebase: `backend/services/embedding_service.py`, `backend/services/bedrock_service.py`, `backend/services/dynamo_service.py`, `backend/services/material_service.py`, `frontend/components/MaterialLibrary.tsx`, `frontend/app/dashboard/page.tsx`

### Secondary (MEDIUM confidence)
- [AWS Bedrock Converse API reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html) — confirmed messages structure alternates user/assistant

### Tertiary (LOW confidence)
- General FastAPI RAG endpoint patterns from community articles — architecture corroborated by existing project conventions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all APIs verified against official docs
- Architecture: HIGH — all service/router patterns directly mirror existing Phase 3 code
- S3 Vectors query API: HIGH — verified method signature and IAM requirements from boto3 official docs
- Bedrock multi-turn: HIGH — verified messages format from official AWS docs
- Pitfalls: HIGH for IAM gap (official docs confirm), MEDIUM for latency estimates (heuristic from known Bedrock characteristics)

**Research date:** 2026-03-16
**Valid until:** 2026-06-16 (S3 Vectors is stable; Bedrock converse API is stable)
