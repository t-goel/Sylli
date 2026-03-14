# Architecture Research

**Domain:** RAG-based study application — serverless AWS backend + Next.js frontend
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Next.js App (Vercel or standalone)                │  │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │  │
│  │   │  Pages/  │  │  Server  │  │  Route   │  │  Next.js   │   │  │
│  │   │  Layout  │  │ Actions  │  │ Handlers │  │ Middleware │   │  │
│  │   └──────────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘   │  │
│  └─────────────────────┼──────────────┼───────────────┼──────────┘  │
└────────────────────────┼──────────────┼───────────────┼─────────────┘
                         │ HTTP + JWT   │               │ JWT verify
                         ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │   Cognito User Pool Authorizer (validates JWT on all routes)  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│   /api/v1/* → Lambda proxy integration                               │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                       LAMBDA (FastAPI + Mangum)                      │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   /syllabus  │  │  /materials  │  │  /chat /quiz │               │
│  │    router    │  │    router    │  │    router    │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                  │                       │
│  ┌──────▼─────────────────▼──────────────────▼───────────────────┐  │
│  │                     Service Layer                              │  │
│  │  SyllabusService │ MaterialService │ RAGService │ QuizService  │  │
│  └──────┬──────────────────┬─────────────────┬────────────────────┘  │
└─────────┼──────────────────┼─────────────────┼──────────────────────┘
          │                  │                 │
┌─────────▼──────────────────▼─────────────────▼──────────────────────┐
│                         AWS DATA LAYER                               │
│                                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │    S3    │  │   DynamoDB   │  │  S3 Vectors  │  │   Bedrock   │  │
│  │  (files) │  │  (metadata)  │  │  (embeddings)│  │ (LLM+embed) │  │
│  └──────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │         Cognito User Pool (user identity store)               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Next.js Middleware | JWT verification before page load, redirect unauthed users | `middleware.ts` using `jose` for edge-compatible JWT verify |
| Next.js Server Actions / Route Handlers | Forward authenticated requests to API Gateway with JWT from cookie | `cookies().get('token')` → `Authorization: Bearer` header |
| API Gateway | Route HTTP traffic, enforce auth via Cognito authorizer | Cognito User Pool Authorizer on all non-auth routes |
| Lambda (FastAPI + Mangum) | Business logic, RAG query execution, quiz generation | Existing pattern; extend with new routers + services |
| SyllabusService | Existing: parse + store syllabus week_map | Existing — extend to link user_id to syllabus |
| MaterialService | Upload, store, auto-categorize materials per syllabus unit | New service; calls Bedrock for category suggestion |
| RAGService | Embed query, retrieve chunks, call Bedrock for answer + citations | New service; calls S3 Vectors QueryVectors + Bedrock Claude |
| QuizService | Generate quiz questions scoped to unit or course | New service; calls RAGService for context, Bedrock for generation |
| Cognito User Pool | Email/password user storage, JWT issuance | Managed AWS service; no Lambda code needed for auth itself |
| S3 (files) | Raw PDF/slide storage | Existing — extend path structure to include `user_id/` |
| DynamoDB | Syllabus metadata, material metadata, user-to-course mapping | Existing — add tables for materials, users |
| S3 Vectors | Vector embeddings for all uploaded material chunks | New AWS service (GA Dec 2025); QueryVectors API |
| Bedrock | Claude 3.5 Sonnet for parsing, RAG generation, quiz gen; Titan/Nova Lite for embeddings | Existing LLM usage — add embedding model invocation |

---

## Recommended Project Structure

```
sylli/
├── backend/                          # Existing FastAPI + Mangum Lambda
│   ├── app.py                        # FastAPI app + Mangum handler
│   ├── routers/
│   │   ├── health.py                 # Existing
│   │   ├── syllabus.py               # Existing — add user_id scoping
│   │   ├── auth.py                   # New: /register, /login (Cognito SDK calls)
│   │   ├── materials.py              # New: upload + categorize endpoints
│   │   ├── chat.py                   # New: RAG tutor endpoint
│   │   └── quiz.py                   # New: quiz generation endpoint
│   ├── services/
│   │   ├── syllabus_service.py       # Existing — extend for user scoping
│   │   ├── bedrock_service.py        # Existing — extend with embed method
│   │   ├── dynamo_service.py         # Existing — extend with new table ops
│   │   ├── s3_service.py             # New: generic file operations
│   │   ├── material_service.py       # New: upload + categorize logic
│   │   ├── rag_service.py            # New: embed + retrieve + generate
│   │   ├── quiz_service.py           # New: quiz prompt construction + generation
│   │   └── cognito_service.py        # New: register/login calls to Cognito
│   └── template.yaml                 # SAM — add new Lambda env vars, Cognito pool
│
└── frontend/                         # New Next.js application
    ├── middleware.ts                  # JWT verification at edge; redirect to /login
    ├── app/
    │   ├── layout.tsx
    │   ├── (auth)/
    │   │   ├── login/page.tsx         # Email/password form → Cognito
    │   │   └── register/page.tsx
    │   ├── (app)/                     # Protected routes
    │   │   ├── dashboard/page.tsx     # Syllabus + material library overview
    │   │   ├── upload/page.tsx        # Syllabus + material upload UI
    │   │   ├── chat/page.tsx          # AI tutor chat interface
    │   │   └── quiz/page.tsx          # Quiz generation + display
    │   └── api/                       # Route handlers (thin proxies if needed)
    ├── lib/
    │   ├── api.ts                     # Typed fetch wrapper; attaches JWT from cookie
    │   └── auth.ts                    # Cognito SDK client-side helpers
    └── components/
        ├── Syllabus/
        ├── MaterialList/
        ├── ChatWindow/
        └── QuizCard/
```

### Structure Rationale

- **`(auth)/` vs `(app)/` route groups:** Next.js App Router groups let middleware distinguish protected from public routes with a single path prefix check — no per-page auth logic needed.
- **`lib/api.ts` fetch wrapper:** Centralizes JWT forwarding and error handling. Server components call this with cookies from `next/headers`; client components call it after reading the token from a non-HttpOnly cookie (or via a server action proxy).
- **`middleware.ts` at edge:** Runs before any page render. Verifies JWT using `jose` (edge-compatible). Unverified requests redirect to `/login`. This eliminates the need for a Lambda authorizer to protect frontend-initiated navigations.
- **API Gateway Cognito authorizer:** Still needed for direct API calls. Acts as the enforcement point for all Lambda routes. The Next.js middleware is defense-in-depth for UX, not the security boundary.

---

## Architectural Patterns

### Pattern 1: Split Auth — Cognito Authorizer on API Gateway + Middleware on Next.js

**What:** Auth is enforced at two points: API Gateway rejects requests without a valid Cognito JWT (HTTP 401), and Next.js middleware redirects unauthenticated browsers to `/login` before rendering any page. Cognito User Pool is the single source of truth for tokens.

**When to use:** Any serverless AWS backend where you want zero auth logic in Lambda functions. API Gateway handles token validation natively — no extra Lambda invocation, no cold starts for auth.

**Trade-offs:**
- Pro: Cognito authorizer adds ~0ms to Lambda invocation (happens before Lambda is called)
- Pro: No auth code needed in FastAPI handlers — `event.requestContext.authorizer.claims.sub` gives user_id
- Con: Cognito setup has non-trivial SAM/CloudFormation configuration
- Con: Next.js middleware JWT verification must use `jose`, not `jsonwebtoken` (Node.js only)

**Example flow:**
```
Browser → Next.js middleware (jose JWT verify from cookie)
  → if invalid: redirect /login
  → if valid: render page

Page → fetch to API Gateway (Authorization: Bearer <token>)
  → Cognito authorizer validates token
  → if invalid: 401 (Next.js shows error)
  → if valid: Lambda receives request with user claims in context
```

### Pattern 2: Async Ingestion Pipeline (S3 Event → Lambda Processor)

**What:** When a student uploads a material PDF, the upload Lambda stores the file in S3 and returns immediately (fast response). An S3 event notification triggers a separate processor Lambda that chunks, embeds, and writes vectors to S3 Vectors. The user polls or receives a status update when embedding is complete.

**When to use:** Mandatory for materials with more than ~2-3 pages. Embedding 50 pages synchronously within the 30s Lambda timeout is not feasible with Bedrock's Titan embedding API (each chunk is a separate API call).

**Trade-offs:**
- Pro: Upload endpoint stays fast (<5s); embedding runs asynchronously
- Pro: Processor Lambda can use a longer timeout (up to 15 minutes for large documents)
- Con: UI needs a loading/processing state indicator after upload
- Con: Two Lambda functions with different roles/timeouts to configure

**Example flow:**
```
POST /materials/upload
  → MaterialService saves file to S3 at users/{user_id}/materials/{material_id}/file.pdf
  → Saves metadata to DynamoDB (status: "processing")
  → Returns 202 Accepted with material_id

S3 Event (s3:ObjectCreated) → EmbedProcessorLambda
  → Reads PDF from S3
  → Chunks text (fixed-size: 500 tokens, 100 token overlap)
  → For each chunk: calls Bedrock Titan Embed to get 1536-dim vector
  → Writes vector + metadata to S3 Vectors index (syllabus-scoped)
  → Updates DynamoDB status to "ready"
```

### Pattern 3: Week-Scoped RAG Retrieval with Metadata Filters

**What:** S3 Vectors supports metadata filters on QueryVectors. Store each embedded chunk with metadata like `{week: "3", material_id: "...", user_id: "..."}`. RAG queries can be scoped to a unit/week by filtering on `week` metadata — no separate index per week needed.

**When to use:** Always. This is the core differentiator for Sylli: week-aware retrieval. Without metadata filtering, the AI tutor gives answers from any week when the student wants only Week 3 content.

**Trade-offs:**
- Pro: One S3 Vectors index per user-course (simple); filtering is handled by the QueryVectors API
- Pro: Filters are evaluated before approximate nearest neighbor search — efficient
- Con: Metadata filter syntax must be learned; needs testing for correctness
- Con: Cross-week queries (full-course quiz) must remove the filter — handle with a flag

**Example:**
```python
# Week-scoped query
response = s3_client.query_vectors(
    VectorBucketName="sylli-vectors",
    IndexName=f"user-{user_id}-course",
    QueryVector=query_embedding,
    TopK=10,
    Filter={"week": {"$eq": "3"}}  # Only Week 3 materials
)

# Full-course quiz — no filter
response = s3_client.query_vectors(
    VectorBucketName="sylli-vectors",
    IndexName=f"user-{user_id}-course",
    QueryVector=query_embedding,
    TopK=20
)
```

### Pattern 4: Lambda Response Streaming for RAG/Chat

**What:** API Gateway + Lambda can be configured with `InvokeMode: RESPONSE_STREAM`. The RAG chat endpoint streams Claude's response tokens back to the client as they're generated, bypassing the 30s timeout and 6MB payload limit.

**When to use:** Chat/tutor endpoint only. Quiz generation can remain synchronous (shorter output). Streaming is required if Claude's response might exceed 30s to complete (likely for complex multi-document retrievals).

**Trade-offs:**
- Pro: Eliminates timeout risk for chat; better UX (progressive rendering)
- Pro: Bedrock's `invoke_model_with_response_stream` API is already supported
- Con: Requires SAM changes (`FunctionUrlConfig` or API Gateway streaming config)
- Con: Frontend must handle streamed chunks (SSE or chunked transfer encoding)
- Con: Mangum does not natively support streaming — may require switching the chat endpoint to a Lambda Function URL directly, bypassing API Gateway proxy for that one route

---

## Data Flow

### Auth Flow (Login)

```
Browser → POST /api/v1/auth/login {email, password}
    → Lambda: cognito_service.initiate_auth(USER_PASSWORD_AUTH)
    → Cognito User Pool: validates credentials, issues tokens
    → Lambda returns: {access_token, id_token, refresh_token}
    → Next.js sets HttpOnly cookie with id_token
    → Middleware uses id_token for subsequent page-load verification
    → API calls use id_token in Authorization header
```

### Material Upload Flow

```
Browser → POST /api/v1/materials/upload (multipart, with JWT)
    → API Gateway: Cognito authorizer validates JWT, injects user_id
    → Lambda: stores file in S3 at users/{user_id}/materials/{id}/
    → Lambda: writes DynamoDB record {material_id, user_id, syllabus_id, week, status: "processing"}
    → Lambda: returns 202 {material_id}
    [async]
    S3 event → EmbedProcessorLambda:
        → reads PDF bytes, extracts text
        → calls Bedrock Titan Embed per 500-token chunk
        → writes vectors to S3 Vectors index with metadata {user_id, week, material_id}
        → updates DynamoDB: status = "ready"
```

### RAG Chat Flow

```
Browser → POST /api/v1/chat {message, week_filter?} (with JWT)
    → API Gateway: validates JWT
    → Lambda RAGService:
        1. Embed query: Bedrock Titan Embed(message) → query_vector
        2. Retrieve: S3 Vectors QueryVectors(query_vector, filter={week}, TopK=10)
        3. Fetch chunk text from DynamoDB/S3 by chunk_id
        4. Construct prompt: [context chunks] + [week_map] + [user message]
        5. Generate: Bedrock Claude 3.5 Sonnet (streaming)
    → Stream tokens back to client via Lambda streaming
    → Client renders tokens progressively
```

### Quiz Generation Flow

```
Browser → POST /api/v1/quiz/generate {week?, num_questions}
    → API Gateway: validates JWT
    → Lambda QuizService:
        1. Fetch week_map from DynamoDB for context
        2. Retrieve relevant chunks from S3 Vectors (filtered by week if specified)
        3. Construct quiz prompt with retrieved content
        4. Call Bedrock Claude (synchronous — structured JSON output)
    → Return JSON array of {question, options, answer, source_material}
```

### State Management

```
User Identity:    Cognito User Pool (source of truth)
                  → JWT in HttpOnly cookie (client session)
                  → user_id injected into all Lambda requests via API Gateway context

Syllabus State:   DynamoDB sylli-syllabus-table (existing)
                  → keyed by syllabus_id, extended with user_id field

Material State:   DynamoDB sylli-materials-table (new)
                  → {material_id, user_id, syllabus_id, week, s3_key, status, chunk_ids[]}

Vector State:     S3 Vectors index per user-course (new)
                  → vectors with metadata {user_id, material_id, week, chunk_index}

Raw Files:        S3 sylli-materials-bucket (new or extend existing)
                  → path: users/{user_id}/materials/{material_id}/{filename}
```

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 users | Current Lambda-per-request model is fine; S3 Vectors sub-second latency holds; no changes needed |
| 100-10K users | Lambda concurrency limits may surface; request reserved concurrency for RAG Lambda; S3 Vectors handles this scale natively |
| 10K+ users | S3 Vectors supports 2B vectors / 10K indexes — no vector store migration needed; DynamoDB auto-scales; Lambda is the main throttle point (request limit increases via AWS support) |

### Scaling Priorities

1. **First bottleneck — Lambda concurrency:** Default 1000 concurrent executions per region. RAG queries that stream for 10-30s each hold Lambda environments. At ~100 simultaneous users, this saturates. Mitigation: reserved concurrency + Provisioned Concurrency for RAG Lambda.
2. **Second bottleneck — Bedrock throughput limits:** Bedrock has per-model invocation rate limits per account. At high volume, embedding generation during ingestion hits limits. Mitigation: request quota increases; implement exponential backoff in EmbedProcessorLambda.

---

## Anti-Patterns

### Anti-Pattern 1: Synchronous Embedding During Material Upload

**What people do:** Embed all chunks inside the upload request handler, within the same Lambda invocation that stores the file.

**Why it's wrong:** A 30-page PDF produces ~100+ chunks. Each Bedrock embedding call takes 100-400ms. That is 10-40+ seconds for embedding alone, exceeding Lambda's 30s timeout. The upload returns an error even though the file was saved.

**Do this instead:** Return 202 immediately after S3 upload. Use an S3 event to trigger a dedicated processor Lambda with up to 15-minute timeout.

### Anti-Pattern 2: One S3 Vectors Index per Week

**What people do:** Create a separate vector index for Week 1, Week 2, etc. to enable per-week retrieval.

**Why it's wrong:** Indexes are not free to create per query. More indexes = more management overhead, more IAM policies, more DynamoDB references. The QueryVectors API natively supports metadata filters — week scoping is a filter, not an index boundary.

**Do this instead:** One index per user-course. Store `week` as vector metadata. Filter at query time.

### Anti-Pattern 3: Storing Auth Tokens in localStorage

**What people do:** After Cognito login, store JWT in `localStorage` and read it on every API call.

**Why it's wrong:** XSS attacks can read `localStorage` and exfiltrate the token. For an MVP with student data (course materials, notes), this is an unnecessary risk.

**Do this instead:** Store the Cognito `id_token` in an HttpOnly, Secure, SameSite=Strict cookie. Server actions and route handlers read it from `next/headers`. Client-side JS never touches the token directly.

### Anti-Pattern 4: Using Bedrock Knowledge Bases Instead of Custom RAG

**What people do:** Connect S3 materials to Bedrock Knowledge Bases for a zero-code RAG pipeline.

**Why it's wrong for Sylli:** Bedrock Knowledge Bases do not support per-user data isolation out of the box. All documents in a Knowledge Base are accessible to all queries — there is no built-in user_id scoping. Implementing it requires separate Knowledge Base instances per user, which is operationally expensive for an MVP.

**Do this instead:** Custom RAG: embed with Bedrock Titan, store in S3 Vectors with user_id metadata filter. Full control over isolation and retrieval scope.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Cognito User Pool | Lambda calls `boto3 cognito-idp initiate_auth`; API Gateway uses native Cognito authorizer (no Lambda needed for validation) | USER_PASSWORD_AUTH flow for email/password MVP |
| S3 Vectors | Lambda calls `boto3 s3vectors` (new client); `put_vectors`, `query_vectors` APIs | GA as of Dec 2025; requires boto3 >= 1.36.x; ARM64 Lambda supported |
| Bedrock Titan Embed | Lambda calls `bedrock-runtime invoke_model` with `amazon.titan-embed-text-v2:0` | 1536-dim vectors; ~100ms per chunk; same IAM role as existing Bedrock usage |
| Bedrock Claude 3.5 Sonnet | Existing integration; extend to use `invoke_model_with_response_stream` for chat | Streaming requires Lambda Function URL or API Gateway HTTP API (not REST API proxy) |
| Next.js ↔ API Gateway | HTTPS fetch from Next.js server actions/route handlers; JWT in Authorization header; CORS configured on API Gateway for frontend origin | Set `Access-Control-Allow-Origin` to Next.js domain; credentials: 'include' for cookie-based auth |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Next.js Middleware ↔ Cognito | Offline JWT verification via `jose` (edge-compatible); validates signature against Cognito JWKS URL | Cache JWKS in memory; do not call Cognito on every request |
| Upload Lambda ↔ EmbedProcessor Lambda | S3 event notification (ObjectCreated) | Decoupled; no direct Lambda-to-Lambda call |
| RAGService ↔ S3 Vectors | boto3 s3vectors client within Lambda; synchronous query (sub-second) | Fits within 30s timeout comfortably |
| RAGService ↔ DynamoDB | Fetch chunk text by chunk_id after vector retrieval | Store chunk text in DynamoDB alongside vector IDs; avoids second S3 read per chunk |
| QuizService ↔ RAGService | Direct Python function call within same Lambda invocation | Both are services in the same FastAPI app |

---

## Build Order Implications

The component dependencies determine phase ordering:

1. **Auth (Cognito + API Gateway authorizer)** — must come first. Without user_id isolation, all subsequent features build on an insecure foundation. Every other component needs user_id in scope.

2. **Material Upload (S3 + DynamoDB + processor Lambda)** — second. Users need materials before RAG can work. The async embedding pipeline is infrastructure that chat and quiz depend on.

3. **Library Navigator (frontend + material listing)** — can be built in parallel with or immediately after upload. No RAG dependency — just reads DynamoDB metadata.

4. **RAG Pipeline (S3 Vectors + embed + retrieve + generate)** — third. Depends on: (a) materials existing in S3, (b) user scoping from auth, (c) vector infrastructure provisioned.

5. **AI Tutor (chat endpoint + streaming frontend)** — fourth. Depends on RAG pipeline. Streaming requires Lambda Function URL configuration (additional SAM change).

6. **Quiz Generator** — fifth. Depends on RAG pipeline. Can reuse retrieved chunks. Simpler than chat (no streaming needed).

---

## Sources

- [Amazon S3 Vectors GA Announcement](https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/) — MEDIUM confidence (page content partially unavailable; corroborated by official docs)
- [S3 Vectors Official Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html) — HIGH confidence
- [Serverless RAG Pipeline on AWS (freeCodeCamp)](https://www.freecodecamp.org/news/how-to-build-a-serverless-rag-pipeline-on-aws-that-scales-to-zero/) — MEDIUM confidence
- [API Gateway + Cognito User Pool Authorizer (AWS Docs)](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html) — HIGH confidence
- [Lambda SnapStart for Python (DEV Community)](https://dev.to/aws-builders/from-seconds-to-milliseconds-fixing-python-cold-starts-with-snapstart-59mn) — MEDIUM confidence
- [RAG on Lambda — Response Streaming Pattern](https://dev.to/aws-heroes/rags-to-riches-part-2-building-on-lambda-2c9g) — MEDIUM confidence
- [Next.js JWT Auth in Middleware (HashBuilds 2025)](https://www.hashbuilds.com/articles/next-js-middleware-authentication-protecting-routes-in-2025) — MEDIUM confidence
- [Building Serverless RAG on AWS — Benchmarks (Loka Engineering Jan 2026)](https://medium.com/loka-engineering/building-rag-systems-on-aws-lessons-from-serverless-and-ec2-benchmarks-165b481a0c95) — LOW confidence (403 on fetch; citation from search snippet only)
- [AWS Prescriptive Guidance — Vector DB Options](https://docs.aws.amazon.com/prescriptive-guidance/latest/choosing-an-aws-vector-database-for-rag-use-cases/vector-db-options.html) — HIGH confidence

---

*Architecture research for: Sylli AI — serverless RAG study application*
*Researched: 2026-03-14*
