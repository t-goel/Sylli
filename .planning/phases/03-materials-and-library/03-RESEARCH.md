# Phase 3: Materials and Library - Research

**Researched:** 2026-03-14
**Domain:** File upload (PDF/PPTX), async embedding pipeline, S3 Vectors, library UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Unit Assignment Flow**
- Inline confirmation: after upload completes, the upload row expands showing the AI-suggested week with [Confirm] and [Change week] buttons
- "Change week" opens a dropdown populated from the parsed week_map (e.g., "Week 3: Data Structures")
- Unconfirmed materials appear in the library immediately under the AI-suggested week with a subtle "Unconfirmed" badge
- Materials are NOT hidden until confirmation — non-blocking flow
- Upload entry point is on the existing dashboard page (extend below the syllabus upload section, above the library)

**Library Layout**
- Sections per week, always expanded — no collapse/accordion
- All weeks from the syllabus are shown, including empty ones ("no materials yet")
- Each material row shows: file type icon (PDF/PPTX) + filename
- Unconfirmed materials show a subtle "Unconfirmed" badge in the library row

**File Viewing**
- Clicking a material opens it directly in a new browser tab via a presigned S3 URL
- URL is generated on-demand each click (no caching) — most secure, same latency as a fetch
- No intermediate details panel — click = open

**Embedding Status Feedback**
- Each material shows a "Processing..." badge that transitions to a checkmark when embedding completes
- Frontend polls the material status endpoint every ~4 seconds until status = 'ready', then clears the interval
- Embedding does NOT start on upload — it triggers after the user confirms the week assignment
- This ensures embeddings are stored with final (user-confirmed) week metadata for filtered retrieval

### Claude's Discretion
- Exact polling interval (3-5s range acceptable)
- Specific CSS/styling for the Unconfirmed badge and Processing indicator
- Whether to create a new `MaterialUpload` component or extend `SyllabusUpload`
- DynamoDB schema for materials table (key structure, attribute names)
- Vector store selection (S3 Vectors vs OpenSearch Serverless — must be AWS-only per project constraint)
- Lambda async invocation pattern for embedding (SNS, SQS, or async Lambda invoke)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MAT-01 | User can upload PDF or PPTX files as course materials | Multipart upload pattern from SyllabusUpload; python-pptx + PyMuPDF for extraction |
| MAT-02 | AI suggests which unit/week an uploaded material belongs to (based on parsed syllabus) | Bedrock converse API already in use; pass week_map + filename to Claude for suggestion |
| MAT-03 | User can confirm or override the AI-suggested unit/week assignment for each material | Inline UI pattern with DynamoDB status update on confirm |
| MAT-04 | Uploaded materials are chunked and embedded asynchronously (non-blocking upload flow) | Async Lambda invocation (InvocationType='Event') after confirm; Titan Embed V2 via bedrock-runtime |
| MAT-05 | Embeddings are stored with user_id and unit/week metadata for filtered retrieval | S3 Vectors put_vectors with metadata {user_id, week_number, material_id, chunk_index} |
| LIB-01 | User can view all uploaded materials organized by unit/week in a chronological timeline | Extend WeekTimeline pattern; GET /api/v1/materials returns list scoped by user_id |
| LIB-02 | User can click a material in the library to view the original file | S3 generate_presigned_url on-demand per click; 300s expiry sufficient |
</phase_requirements>

---

## Summary

Phase 3 builds on a fully functional Phase 2 codebase. All backend patterns (FastAPI router, DynamoDB service, S3 upload, Bedrock invocation, JWT auth) are established and reusable. The new work falls into four areas: (1) material file storage with text extraction for PDF and PPTX, (2) AI-assisted week assignment via Bedrock, (3) async embedding into S3 Vectors after user confirmation, and (4) a library UI extending the existing WeekTimeline component.

The critical architectural decision (Claude's discretion) is the vector store selection. S3 Vectors is now generally available (GA since December 2025), has a boto3 client (`s3vectors`), and integrates naturally with the existing AWS-only stack. The sole gotcha: the Lambda runtime ships an older boto3 that predates s3vectors — the fix is to bundle a recent boto3 in the deployment package (boto3 >= 1.39.5). This is standard practice and well-documented.

The async embedding pipeline uses Lambda's native async invocation (`InvocationType='Event'`), which fires a second Lambda and immediately returns 202. The confirming endpoint triggers this background Lambda, which extracts text, chunks it, calls Titan Embed V2, and writes vectors to S3 Vectors with user_id + week metadata. The main Lambda then updates the material's DynamoDB record from `pending` to `ready`.

**Primary recommendation:** Use S3 Vectors (boto3 s3vectors client) with Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`, 1024 dimensions, cosine distance). Extract PDF text with PyMuPDF and PPTX text with python-pptx. Trigger embedding via async Lambda invoke from the confirm endpoint.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| boto3 (s3vectors client) | >= 1.39.5 | Vector storage and similarity search | Only AWS-native vector store; GA since Dec 2025; built-in metadata filtering |
| amazon.titan-embed-text-v2:0 | current | Generate text embeddings | Already using Bedrock; no new dependencies; 8192 token input; 1024 dim output |
| PyMuPDF (fitz) | 1.27.x | Extract text from PDF files | Best-in-class text extraction; ARM64 wheel available (~24 MB compressed); no system deps |
| python-pptx | 1.0.x | Extract text from PPTX files | Pure Python; small package (~1 MB); no system dependencies; standard for .pptx |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| boto3 lambda client | bundled | Async Lambda invocation | Called from confirm endpoint to trigger embedding worker |
| boto3 s3 client | bundled | Presigned URL generation, material file storage | Already in use; reuse existing pattern from syllabus_service.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| S3 Vectors | OpenSearch Serverless | OpenSearch Serverless has higher baseline cost ($0.24/OCU-hr minimum); S3 Vectors is pay-per-request with no minimum — better for a student project at low volume |
| S3 Vectors | Pinecone | Pinecone violates the AWS-only constraint established in Phase 1 design notes |
| Async Lambda invoke | SQS + Lambda trigger | SQS adds SAM resources and complexity; async invoke is sufficient for single-user project with no burst concern |
| PyMuPDF | pdfplumber / pypdf | PyMuPDF has better text positioning and layout; pypdf is lighter but lower quality extraction |

**Installation (add to backend/requirements.txt):**
```bash
boto3>=1.39.5
PyMuPDF
python-pptx
```

**Note:** boto3 must be pinned >= 1.39.5 and bundled in the SAM deployment package because the Lambda runtime's built-in boto3 is too old to include the `s3vectors` client.

---

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── routers/
│   └── materials.py          # Upload, confirm, list, presigned URL endpoints
├── services/
│   ├── material_service.py   # File upload, AI week suggestion, DynamoDB ops
│   ├── embedding_service.py  # Text extraction, chunking, Titan embed, S3 Vectors write
│   └── dynamo_service.py     # Extend with materials table operations
├── workers/
│   └── embed_worker.py       # Lambda handler for async embedding job
└── app.py                    # Register materials router

frontend/
├── components/
│   ├── MaterialUpload.tsx     # New component (mirrors SyllabusUpload; accepts PDF + PPTX)
│   ├── MaterialLibrary.tsx    # Library view (extends WeekTimeline aesthetic)
│   └── WeekTimeline.tsx       # Existing; untouched
└── app/dashboard/
    └── page.tsx               # Add MaterialUpload + MaterialLibrary sections
```

### Pattern 1: Material Upload — Multipart with Auth (mirrors SyllabusUpload)
**What:** Raw `fetch` with FormData, no Content-Type header, Authorization Bearer token
**When to use:** All file upload endpoints — do NOT use `apiFetch` which forces Content-Type: application/json

```typescript
// Source: mirrors frontend/components/SyllabusUpload.tsx pattern
const token = localStorage.getItem("token")
const formData = new FormData()
formData.append("file", file)
const res = await fetch(`${API_BASE}/api/v1/materials`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  // Do NOT set Content-Type — browser sets multipart boundary automatically
  body: formData,
})
```

### Pattern 2: DynamoDB Materials Table Schema
**What:** Single-table material records keyed by material_id (UUID), with user_id as a GSI for listing
**When to use:** All DynamoDB operations for materials

Recommended DynamoDB item structure:
```python
{
    "material_id": str(uuid4()),          # Partition key (UUID)
    "user_id": str,                       # GSI partition key for listing by user
    "filename": str,
    "s3_key": str,                        # e.g. "materials/{material_id}/{filename}"
    "file_type": "pdf" | "pptx",
    "week_number": int,                   # AI-suggested or user-confirmed
    "week_confirmed": bool,               # False until user clicks Confirm
    "embed_status": "pending" | "processing" | "ready",
    "uploaded_at": str,                   # ISO 8601 UTC
}
```

GSI for listing user's materials:
- GSI name: `user_id-index`
- Partition key: `user_id`
- Sort key: `uploaded_at` (chronological ordering)

### Pattern 3: Async Embedding Trigger
**What:** After user confirms week, the confirm endpoint invokes an embedding Lambda asynchronously and returns immediately to the frontend
**When to use:** After the user clicks "Confirm" — NOT on upload

```python
# Source: AWS Lambda boto3 async invocation docs
import json
import boto3

lambda_client = boto3.client("lambda")

def trigger_embedding_async(material_id: str, user_id: str, week_number: int):
    """Fire-and-forget: start embedding Lambda, return immediately."""
    payload = {
        "material_id": material_id,
        "user_id": user_id,
        "week_number": week_number,
    }
    lambda_client.invoke(
        FunctionName=os.getenv("EMBED_FUNCTION_NAME"),  # SAM env var
        InvocationType="Event",  # Async — returns 202, doesn't wait
        Payload=json.dumps(payload),
    )
    # No return value needed — response StatusCode 202 means queued
```

### Pattern 4: S3 Vectors — Write Embeddings
**What:** After chunking and embedding text, write each chunk as a vector with metadata
**When to use:** In the embedding worker Lambda, after Titan embed call

```python
# Source: boto3 s3vectors docs (put_vectors method)
s3v = boto3.client("s3vectors", region_name=os.getenv("AWS_REGION", "us-east-1"))

s3v.put_vectors(
    vectorBucketName=os.getenv("VECTOR_BUCKET_NAME"),
    indexName=os.getenv("VECTOR_INDEX_NAME"),
    vectors=[
        {
            "key": f"{material_id}#chunk#{chunk_idx}",
            "data": {"float32": embedding},   # list of 1024 floats
            "metadata": {
                "user_id": user_id,
                "material_id": material_id,
                "week_number": week_number,
                "chunk_index": chunk_idx,
                "source_text": chunk_text[:500],  # truncate for metadata
            },
        }
    ],
)
```

### Pattern 5: S3 Vectors — Query with Metadata Filter (Phase 4 prep)
**What:** Query vectors filtered by user_id and optionally week_number
**When to use:** Phase 4 AI Tutor — included here so Phase 3 stores metadata correctly

```python
# Source: boto3 query_vectors docs
results = s3v.query_vectors(
    vectorBucketName=os.getenv("VECTOR_BUCKET_NAME"),
    indexName=os.getenv("VECTOR_INDEX_NAME"),
    topK=10,
    queryVector={"float32": query_embedding},
    filter={"user_id": user_id},       # Phase 4: add {"week_number": N} for scoped search
    returnMetadata=True,
    returnDistance=True,
)
```

### Pattern 6: S3 Presigned URL (on-demand per click)
**What:** Generate a time-limited URL for the frontend to open the file in a new tab
**When to use:** When user clicks a material in the library

```python
# Source: boto3 s3 generate_presigned_url docs
s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": MATERIALS_BUCKET, "Key": s3_key},
    ExpiresIn=300,  # 5 minutes — enough to open, re-generated each click
)
```

### Pattern 7: Text Extraction
**What:** Extract plain text from PDF or PPTX for chunking and embedding
**When to use:** In the embedding worker Lambda before chunking

```python
# PDF — Source: PyMuPDF docs
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)

# PPTX — Source: python-pptx docs
from pptx import Presentation
import io

def extract_text_from_pptx(pptx_bytes: bytes) -> str:
    prs = Presentation(io.BytesIO(pptx_bytes))
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
    return "\n".join(texts)
```

### Pattern 8: Text Chunking
**What:** Split extracted text into overlapping chunks before embedding
**When to use:** After text extraction, before Titan embed calls

```python
# Simple fixed-size character chunking with overlap
CHUNK_SIZE = 1500     # characters (~400 tokens at ~3.75 chars/token)
CHUNK_OVERLAP = 200   # characters

def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c.strip()]  # skip whitespace-only chunks
```

### Pattern 9: Frontend Status Polling
**What:** Poll a material's status endpoint until embed_status = 'ready', then stop
**When to use:** After user confirms week assignment

```typescript
// Poll every 4 seconds until ready
function pollEmbedStatus(materialId: string, onReady: () => void) {
  const interval = setInterval(async () => {
    const res = await apiFetch(`/api/v1/materials/${materialId}/status`)
    if (res.ok) {
      const data = await res.json()
      if (data.embed_status === "ready") {
        clearInterval(interval)
        onReady()
      }
    }
  }, 4000)
  return interval  // caller can cancel if component unmounts
}
```

### Anti-Patterns to Avoid
- **Starting embedding on upload:** Embedding must only start AFTER user confirms the week, so vectors are stored with the final (not AI-suggested) week metadata
- **Caching presigned URLs:** Each click must generate a fresh URL — cached URLs can expire and break the open-in-tab flow
- **Using apiFetch for file uploads:** apiFetch sets `Content-Type: application/json` which breaks multipart/form-data; use raw fetch with FormData
- **Using Lambda runtime boto3 for s3vectors:** The built-in Lambda boto3 is too old; boto3 >= 1.39.5 must be in the deployment package
- **Storing full chunk text in vector metadata:** S3 Vectors metadata has size limits; truncate to ~500 chars or store a chunk reference instead of full text

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | PyMuPDF (fitz) | Handles complex layouts, multi-column, scanned text detection; ~24 MB ARM64 wheel |
| PPTX text extraction | XML parsing of .pptx zip | python-pptx | PPTX is Open XML; python-pptx handles all shape types, text frames, tables |
| Vector similarity search | Custom cosine distance over DynamoDB | S3 Vectors | ANN index built-in, metadata filtering, no infrastructure to manage |
| Text splitting | Custom regex splitter | Simple chunking (see Pattern 8) | Fixed-size with overlap is well-proven for slides/lecture notes; no extra library needed |
| Embedding model | Custom embeddings | Titan Text Embeddings V2 | Already using Bedrock; consistent infrastructure; 1024 dimensions optimal for RAG |

**Key insight:** The embedding pipeline looks complex but breaks down into established, small operations — each of which has a standard library or AWS service. The only custom code is glue logic.

---

## Common Pitfalls

### Pitfall 1: S3 Vectors "Unknown service: s3vectors" in Lambda
**What goes wrong:** Lambda runtime ships an old boto3 that doesn't include the s3vectors client. Runtime error on first call.
**Why it happens:** Lambda's bundled boto3 predates the December 2025 S3 Vectors GA. The s3vectors client requires boto3 >= 1.39.5.
**How to avoid:** Add `boto3>=1.39.5` to `requirements.txt`. SAM bundles `requirements.txt` into the deployment package, overriding the runtime boto3.
**Warning signs:** `botocore.exceptions.UnknownServiceError: Unknown service: 's3vectors'` in CloudWatch logs

### Pitfall 2: PyMuPDF glibc Incompatibility on Lambda ARM64
**What goes wrong:** `pip install pymupdf` may pull a wheel built for a newer glibc than what Lambda ARM64 Python 3.13 provides.
**Why it happens:** PyMuPDF ARM64 wheel targets `manylinux_2_28_aarch64`. Lambda ARM64 Python 3.13 runtime's glibc version needs validation.
**How to avoid:** Use `sam build --use-container` (Docker) to build on the actual Lambda ARM64 environment. This ensures the correct wheel is selected.
**Warning signs:** `ImportError: /lib/aarch64-linux-gnu/libc.so.6: version 'GLIBC_2.32' not found` in Lambda logs

### Pitfall 3: Embedding Starts Before User Confirms Week
**What goes wrong:** Embeddings are stored with the AI-suggested week, which the user may override. Phase 4 retrieval gets wrong week metadata.
**Why it happens:** Embedding triggered from the upload endpoint instead of the confirm endpoint.
**How to avoid:** embed_status is `null` or absent until the user hits the confirm endpoint; the confirm endpoint sets embed_status = 'processing' and triggers the async Lambda. The upload endpoint only stores the file and returns the AI suggestion.
**Warning signs:** Materials in Phase 4 retrieval return wrong weeks; users complain AI answers are off-topic

### Pitfall 4: DynamoDB User-Scoped Listing Without GSI
**What goes wrong:** Listing all materials for a user requires a full table scan (expensive and slow) because the partition key is material_id.
**Why it happens:** Only a primary key on material_id was defined; no GSI for user_id.
**How to avoid:** Define a GSI on user_id (partition key) + uploaded_at (sort key) at table creation time. CloudFormation GSIs cannot be added to existing tables without recreation.
**Warning signs:** ListMaterials endpoint does a full scan; cost increases with data volume

### Pitfall 5: frontend polls indefinitely if embed worker crashes
**What goes wrong:** If the embed Lambda fails silently, embed_status stays 'processing' forever; frontend polls forever.
**Why it happens:** Async Lambda invocation failures don't propagate to the caller.
**How to avoid:** Embed worker catches all exceptions and calls DynamoDB to set embed_status = 'error' in the finally block. Frontend polls for 'ready' OR 'error' and stops on either.

### Pitfall 6: PPTX File Accept Filter on Input Element
**What goes wrong:** `<input accept=".pptx">` alone may not work on all browsers; some require the MIME type too.
**Why it happens:** Browser inconsistency in accept attribute handling.
**How to avoid:** Use `accept=".pdf,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation"` on the input element.

---

## Code Examples

### S3 Vector Index Setup (one-time, via SAM or manual)
```python
# Source: boto3 create_index docs
s3v = boto3.client("s3vectors")
s3v.create_vector_bucket(vectorBucketName="sylli-vectors")
s3v.create_index(
    vectorBucketName="sylli-vectors",
    indexName="materials-index",
    dataType="float32",
    dimension=1024,               # Matches Titan Embed V2 default output
    distanceMetric="cosine",
    metadataConfiguration={
        # user_id, material_id, week_number, chunk_index are all filterable
        "nonFilterableMetadataKeys": ["source_text"]  # source_text too large to index
    },
)
```

### Titan Embed V2 Call
```python
# Source: AWS Bedrock Titan Embedding Models docs
import json
import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def embed_text(text: str) -> list[float]:
    """Embed text using Titan Text Embeddings V2. Max 8192 tokens input."""
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text, "dimensions": 1024}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]  # list of 1024 floats
```

### AI Week Suggestion via Bedrock
```python
# Extend bedrock_service.py — mirrors parse_syllabus_with_bedrock pattern
def suggest_week_for_material(filename: str, week_map: dict) -> int:
    """Given a filename and week_map, ask Claude which week this material belongs to."""
    weeks_summary = "\n".join(
        f"Week {w['week']}: {w['topic']}" for w in week_map.get("weeks", [])
    )
    prompt = (
        f"Given this course week schedule:\n{weeks_summary}\n\n"
        f"Which week number does the file '{filename}' most likely belong to? "
        f"Reply with ONLY the integer week number."
    )
    response = bedrock.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
    )
    raw = response["output"]["message"]["content"][0]["text"].strip()
    return int(raw)
```

### Material Status Endpoint (polling target)
```python
# backend/routers/materials.py
@router.get("/materials/{material_id}/status", tags=["materials"])
async def get_material_status(
    material_id: str,
    user_id: str = Depends(get_current_user),
):
    """Return embed_status for polling. Returns 'pending', 'processing', 'ready', or 'error'."""
    item = get_material(material_id, user_id)  # returns None on ownership mismatch (anti-enum)
    if item is None:
        raise HTTPException(status_code=404, detail="Material not found.")
    return {"embed_status": item.get("embed_status", "pending")}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pinecone (external) | S3 Vectors (AWS-native) | Dec 2025 (GA) | No external vendor; same boto3 pattern as rest of stack |
| Amazon Textract for PDF text | PyMuPDF direct extraction | 2023-2025 | PyMuPDF faster, cheaper, no extra service; Textract reserved for scanned/image PDFs |
| Lambda background processing via SNS | Direct async Lambda invoke | Always valid | Fewer SAM resources; SNS only needed at scale or when fan-out is required |
| Titan Embed V1 (1536 dims) | Titan Embed V2 (1024 dims default) | 2024 | V2 better quality, lower cost, variable dimensions, 100+ language support |

**Deprecated/outdated:**
- `invoke_async` (boto3 Lambda method): Deprecated — use `invoke(InvocationType='Event')` instead
- Bedrock Knowledge Bases: Explicitly excluded from this project — no per-user isolation (see REQUIREMENTS.md Out of Scope)

---

## Open Questions

1. **PyMuPDF glibc on Lambda ARM64 Python 3.13**
   - What we know: PyMuPDF ARM64 wheel requires `manylinux_2_28` (glibc 2.28+)
   - What's unclear: Lambda ARM64 Python 3.13 runtime's exact glibc version
   - Recommendation: First build task in Wave 1 should run `sam build --use-container` and verify no import errors. If PyMuPDF fails, fall back to `pypdf` (pure Python, lower extraction quality but zero native deps).

2. **Deployment package size with boto3 + PyMuPDF + python-pptx**
   - What we know: PyMuPDF ARM64 wheel is ~24 MB compressed; boto3 is ~10 MB; python-pptx is ~1 MB; Lambda limit is 250 MB unzipped
   - What's unclear: Total unzipped size after SAM build — needs validation
   - Recommendation: Run `sam build --use-container && du -sh .aws-sam/build/SylliFunction/` early in planning. If size is near the limit, consider a Lambda Layer for PyMuPDF.

3. **S3 Vectors vector bucket + index provisioning**
   - What we know: Vector buckets and indexes must be created before the embedding worker can write
   - What's unclear: Whether SAM/CloudFormation has native support for creating S3 Vectors resources, or if a one-time manual/CDK step is needed
   - Recommendation: Create vector bucket and index in a Wave 0 setup step (boto3 script or AWS CLI) and document the commands; add environment variables to template.yaml. Do NOT block implementation on CloudFormation native support.

---

## Sources

### Primary (HIGH confidence)
- `https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors.html` — s3vectors client API (create_index, put_vectors, query_vectors parameters)
- `https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors/client/put_vectors.html` — put_vectors full parameter reference
- `https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors/client/query_vectors.html` — query_vectors with metadata filtering
- `https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors/client/create_index.html` — create_index dimension + distance metric params
- `https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html` — Titan Embed V2 model ID, token limit, dimensions, invoke_model usage
- `https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html` — async Lambda invocation (InvocationType='Event')
- `https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html` — presigned URL generation pattern
- `https://pypi.org/project/PyMuPDF/` — PyMuPDF ARM64 wheel size (~24 MB), glibc requirement

### Secondary (MEDIUM confidence)
- `https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-vectors-generally-available/` — S3 Vectors GA announcement, December 2025
- `https://repost.aws/questions/QUtQDRYoF2QxyJas4SUWGVhQ/s3-vector-boto3-error-in-lambda` — boto3 >= 1.39.5 requirement for Lambda s3vectors support
- `https://repost.aws/questions/QUOR_WMSOZTjCucVVZbWIOaA/error-unknownserviceerror-unknown-service-s3vectors` — confirms bundling boto3 in deployment package as the fix

### Tertiary (LOW confidence)
- General chunking strategy guidance (chunk size 400-512 tokens, 10-20% overlap) from multiple RAG blog posts — use as starting point, not gospel

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — S3 Vectors GA confirmed; Titan Embed V2 confirmed via official docs; PyMuPDF/python-pptx are established libraries
- Architecture: HIGH — all patterns mirror or extend existing Phase 2 code; async Lambda pattern is well-documented
- Pitfalls: HIGH for boto3/PyMuPDF compatibility issues (confirmed by community reports); MEDIUM for chunk sizing (empirical starting point)

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (30 days — S3 Vectors is GA and stable; Titan Embed V2 stable)
