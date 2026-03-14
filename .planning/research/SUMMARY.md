# Project Research Summary

**Project:** Sylli AI — RAG-based study application
**Domain:** Syllabus-first AI tutor and quiz generator on serverless AWS
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH

## Executive Summary

Sylli is a brownfield project: a FastAPI + Lambda + Bedrock backend already exists with syllabus upload, S3 file storage, DynamoDB metadata storage, and a structured `week_map` parsed from syllabi. The work ahead is additive — authentication, a RAG pipeline for uploaded course materials, an AI tutor chat interface, and a quiz generator — plus a new Next.js frontend. The recommended approach is to build strictly in dependency order: auth first (data model cannot be safely retrofitted), then material upload with async embedding, then RAG-powered AI features on top. The existing `week_map` structure is Sylli's key competitive differentiator, enabling week-scoped retrieval and organization that flat-file competitors like NotebookLM cannot match.

The core technical decision is the vector store. The stack research recommends Pinecone Serverless (free tier, zero cost at MVP scale, true serverless) over AWS-native options: OpenSearch Serverless costs $174-350/month at minimum, and FAISS in Lambda is non-persistent. Pinecone is not AWS-native but is the pragmatic choice. For everything else, the stack stays fully AWS: Titan Text Embeddings V2 via Bedrock for embeddings (already in the account), S3 Vectors (GA December 2025) for vector storage as an AWS-native alternative if Pinecone's third-party status is disqualifying, and LlamaIndex for RAG orchestration. Authentication uses custom JWT cookies with PyJWT and pwdlib — Cognito adds unnecessary complexity for a single-developer MVP, and passlib is a hard blocker on Python 3.13 due to PEP 594.

Two existing bugs must be fixed before any new feature ships: the `json.loads()` call in `bedrock_service.py` has no error handling (a real PDF will eventually crash it with a 500 that exposes internal errors), and the synchronous Bedrock call pattern will timeout on real course materials. An async job pattern — upload returns 202, S3 event triggers a processor Lambda — is mandatory for the embedding pipeline and is the correct fix for both issues. Every other feature depends on these foundations being stable.

## Key Findings

### Recommended Stack

The existing backend (Python 3.13, FastAPI, Mangum, AWS Lambda ARM64, SAM, S3, DynamoDB, Bedrock Claude 3.5 Sonnet, boto3) requires no changes. Additions are: LlamaIndex for RAG orchestration, Pinecone Serverless for vector storage, Titan Text Embeddings V2 for embedding, PyMuPDF for PDF text extraction, python-pptx for PowerPoint extraction, PyJWT + pwdlib[argon2] for auth. The frontend is a new Next.js 15 app with TypeScript, Tailwind CSS 4, shadcn/ui, TanStack Query, React Hook Form + Zod, and Zustand.

**Core technologies:**
- **Titan Text Embeddings V2** (`amazon.titan-embed-text-v2:0`): embedding generation — already in the AWS account, no egress cost, 8192 token input limit, 512-dim output for cost efficiency
- **Pinecone Serverless**: vector store — true serverless with zero monthly minimum on Starter tier; use 512-dim vectors to match Titan output
- **LlamaIndex** (0.14.x): RAG orchestration — purpose-built for document RAG, better document ingestion pipeline than LangChain, 35% better retrieval accuracy for document-heavy applications
- **PyMuPDF** (1.25.x): PDF extraction — fastest Python PDF extractor (42ms vs 2.5s for pdfminer), better layout handling for lecture slides
- **python-pptx** (1.x): PowerPoint extraction — only pure-Python library for .pptx text extraction
- **PyJWT** (2.11.x) + **pwdlib[argon2]** (0.2.x): authentication — PyJWT is pure Python (no ARM64 packaging issues), pwdlib is the FastAPI-recommended passlib replacement for Python 3.13
- **Next.js 15** + **Tailwind 4** + **shadcn/ui** + **TanStack Query 5**: frontend stack — 2025/2026 community standard for API-backed Next.js applications

**Critical version warnings:**
- Do not use `passlib` — incompatible with Python 3.13 (PEP 594 removes `crypt`)
- Do not use `python-jose` — unmaintained since 2022, active CVEs
- Do not use `pinecone-client` (old package name) — deprecated, use `pinecone >= 5.1.0`
- `pymupdf` requires ARM64 build: `sam build --use-container`
- Lambda deployment package may approach 250 MB limit; use Lambda layers for heavy deps

### Expected Features

The syllabus `week_map` is already built. Everything else is new.

**Must have (table stakes):**
- Email/password auth with JWT sessions — gates all data behind user accounts; data model cannot be safely added post-hoc
- Material upload (PDF, PPTX) with S3 storage — extends existing syllabus upload
- Library navigator organized by week — surfaces the `week_map` that is Sylli's structural advantage over competitors
- RAG pipeline (embed uploaded materials, store vectors, semantic retrieval) — technical foundation everything else depends on
- AI tutor chat with inline source citations — core value proposition; citations are the most-praised NotebookLM feature and the primary trust mechanism
- Quiz generator (multiple choice + short answer, unit-scoped, instant feedback) — second major value proposition
- Auto-categorization of uploads to suggest a week — reduces manual friction, leverages existing Bedrock integration

**Should have (competitive differentiators):**
- Week-aware AI tutor context injection — differentiates from flat PDF chatbots
- Streaming AI chat responses — reduces perceived latency; reduces timeout risk
- Quiz explanation drill-down with source passage — high value-to-effort ratio
- Quiz scoped to week ranges (e.g., "Weeks 3-5") — critical for midterm/final prep
- Password reset flow — required before any public access

**Defer (v2+):**
- Multi-course support — massive data model complexity; only after single-course is proven
- Spaced repetition / adaptive quiz scheduling — requires persistent score tracking
- Flashcard mode — quiz format covers the same mechanism; defer unless research shows gap
- Audio/voice interface — separate technical track; reassess if NotebookLM audio proves market demand
- Collaborative/shared courses — multi-tenant auth; premature at MVP
- Mobile native app — web-responsive first; native only if usage data justifies it

### Architecture Approach

The architecture is a serverless AWS backend with a decoupled Next.js frontend. Auth is enforced at two layers: API Gateway validates Cognito JWTs before Lambda is invoked (zero Lambda cold-start cost for auth), and Next.js middleware using `jose` redirects unauthenticated browsers before page render. Material upload is decoupled from embedding via S3 event notifications: the upload endpoint returns 202 immediately, an `EmbedProcessorLambda` triggered by S3 ObjectCreated handles chunking and embedding asynchronously. Week-scoped retrieval is implemented via vector metadata filters on the Pinecone (or S3 Vectors) index — one index per user-course, with `week` as a filterable metadata field.

**Major components:**
1. **Next.js frontend** — App Router with `(auth)/` and `(app)/` route groups; middleware.ts for JWT verification at edge; typed fetch wrapper in `lib/api.ts`
2. **API Gateway + Lambda (FastAPI + Mangum)** — existing pattern extended with new routers: `auth`, `materials`, `chat`, `quiz`
3. **EmbedProcessorLambda** — separate Lambda triggered by S3 events; 15-minute timeout for async embedding of uploaded materials
4. **MaterialService** — upload + auto-categorize logic; calls Bedrock for week suggestion
5. **RAGService** — embed query, retrieve chunks with week filter, call Bedrock Claude for answer with citations
6. **QuizService** — retrieve context chunks, construct quiz prompt, return structured JSON with source references
7. **Pinecone (or S3 Vectors)** — vector index per user-course with metadata: `{user_id, week, material_id, chunk_index}`
8. **DynamoDB** — extended with `materials` table; all items keyed with `user_id` partition component

### Critical Pitfalls

1. **Synchronous Bedrock calls timing out** — Implement async job pattern (S3 event → EmbedProcessorLambda) before building any new Bedrock-touching feature. Set explicit botocore timeout (`connect_timeout=5, read_timeout=25`) as an interim measure. This is infrastructure, not polish.

2. **Bedrock JSON parse crash with no recovery (existing bug)** — The current `json.loads()` in `bedrock_service.py` line 56 has no error handling. Fix immediately: add try-catch with markdown code fence extraction fallback and Pydantic schema validation. Never surface raw Bedrock output to the client.

3. **Auth added after data exists** — Adding `user_id` to the DynamoDB partition key after records exist requires a table rebuild. Auth must be Phase 1, and all subsequent table schemas must include `user_id` from day one.

4. **Poor chunking strategy breaking RAG quality** — Fixed-size character chunking applied to lecture slides produces empty or fragmented chunks. Use page-boundary chunking for PDFs (one chunk per slide, sub-chunked only if over token limit) with metadata: `{week, material_id, page_number}`. Evaluate retrieval precision on real lecture slides before building the tutor.

5. **Quiz generation producing hallucinated questions** — LLMs draw from training data unless retrieval is strictly enforced in the prompt. Retrieved chunks must be the exclusive source; prompt must explicitly exclude outside knowledge. Validate by testing with niche topics that only appear in uploaded materials.

## Implications for Roadmap

Based on dependency analysis across all four research files, the natural phase structure is:

### Phase 1: Foundation and Tech Debt
**Rationale:** Two existing bugs (JSON parse crash, no async pattern) will break every subsequent feature if not fixed first. This phase also establishes observability so later phases can be debugged. Zero new features ship to users but the platform becomes stable.
**Delivers:** Bug-free syllabus parsing, async job infrastructure, structured logging across all Lambda functions, boto3 retry configuration on all AWS SDK clients, Pydantic validation on all Bedrock outputs
**Addresses:** Pitfall 2 (JSON parse crash — existing bug), Pitfall 1 (sync Bedrock timeout — architectural prerequisite), technical debt patterns (catch-all exceptions, missing retries, unpinned dependencies)
**Avoids:** Shipping features on a broken foundation that requires immediate rewrite

### Phase 2: Authentication and Data Model
**Rationale:** Auth is the gating dependency for every other feature. The `user_id` partition key decision on DynamoDB tables must be made before any new data is written — it cannot be added later without rebuilding tables. This phase also determines the frontend architecture.
**Delivers:** Email/password registration and login, JWT in httpOnly cookie, API Gateway Cognito authorizer protecting all routes, `user_id` scoping on all existing and new DynamoDB tables, Next.js frontend scaffold with protected route groups and middleware, existing syllabus endpoints retrofitted with user isolation
**Addresses:** Pitfall 3 (open endpoints + missing data ownership), table stakes feature (auth)
**Uses:** PyJWT, pwdlib[argon2], Next.js Middleware, Cognito User Pool
**Research flag:** Standard patterns — well-documented Cognito + API Gateway + FastAPI + Next.js middleware integration; skip deeper research

### Phase 3: Material Upload and Library Navigator
**Rationale:** Users need uploaded materials before RAG can work. The async ingestion pipeline (the fix for synchronous embedding timeout) must be built here. The library navigator is cheap to build (reads existing DynamoDB metadata) and delivers immediate visible value after upload.
**Delivers:** PDF and PPTX upload UI and API, auto-categorization (Bedrock suggests week → user confirms), S3 storage under `user_id/` namespacing, EmbedProcessorLambda (async chunking + embedding), DynamoDB materials table, library navigator showing materials organized by week
**Addresses:** Table stakes (file upload, course structure visibility), differentiator (syllabus-first organization, auto-categorization)
**Implements:** Async ingestion pattern (Pattern 2 from ARCHITECTURE.md), MaterialService, EmbedProcessorLambda
**Avoids:** Pitfall 1 (sync embedding timeout) by decoupling upload from embedding
**Research flag:** S3 Vectors API and Pinecone client API need validation against actual boto3 version in Lambda environment; confirm `s3vectors` client availability on ARM64 Lambda with current boto3

### Phase 4: RAG Pipeline and AI Tutor
**Rationale:** RAG is the critical path. Quiz generation depends on it, and it cannot be built until materials exist in the vector store (Phase 3). This is the highest-complexity, highest-value phase.
**Delivers:** Vector storage with week-scoped metadata, semantic retrieval with metadata filters, AI tutor chat endpoint with week-aware context injection, inline source citations in responses, streaming response support (Lambda Function URL for chat), chat UI
**Addresses:** Table stakes (AI chat grounded in course materials, inline source citations), differentiator (week-aware AI tutor context, cross-material synthesis)
**Uses:** LlamaIndex SentenceSplitter (512-token chunks, 64-token overlap), Titan Text Embeddings V2 via Bedrock, Pinecone Serverless, Bedrock Claude 3.5 Sonnet streaming
**Avoids:** Pitfall 4 (poor chunking — use page-boundary chunking not fixed-size), Anti-Pattern 2 (one index per week — use metadata filters instead)
**Research flag:** Needs research on LlamaIndex + Bedrock Titan integration specifics and Pinecone metadata filter syntax. Streaming Lambda via Function URL requires SAM configuration validation.

### Phase 5: Quiz Generator
**Rationale:** Quiz generation depends directly on RAG quality from Phase 4. Building it before retrieval is validated risks shipping a hallucination-prone quiz that damages user trust and is difficult to fix retroactively.
**Delivers:** Quiz generation endpoint scoped to unit or full course, multiple choice and short answer question types, immediate answer feedback with explanation, source references on each question, quiz UI
**Addresses:** Table stakes (quiz generation, instant quiz feedback), differentiator (explanation drill-down, week-scoped quizzes)
**Avoids:** Pitfall 5 (quiz hallucination — retrieved chunks must be exclusive source; validate with niche topics)
**Research flag:** Standard patterns for structured JSON output from Bedrock (tool use / function calling API). Skip deeper research.

### Phase 6: Polish and Hardening
**Rationale:** Features that raise quality without adding core functionality. Add when core loop (upload → tutor → quiz) is validated working.
**Delivers:** Streaming AI chat if not in Phase 4, password reset flow, quiz week-range scoping ("Weeks 3-5"), cold start mitigation (Provisioned Concurrency for tutor Lambda), error states that explain what went wrong, loading indicators, security hardening (IAM tightening, S3 public access block, magic byte file validation)
**Addresses:** Table stakes (loading indicators, error states), P2 features (streaming, password reset, quiz range scoping)

### Phase Ordering Rationale

- Phases 1-2 are infrastructure: no user-visible features, but they are required for everything else to be stable and secure.
- Phase 3 before Phase 4 because RAG requires materials to exist in the vector store.
- Phase 5 after Phase 4 because quiz quality depends entirely on retrieval quality.
- Phase 6 last because it optimizes a working system rather than building a missing one.
- The `week_map` existing on the backend collapses what would otherwise be two phases (syllabus parsing + material organization) into a single phase advantage — auto-categorization and library navigation are cheaper to build than they would be from scratch.

### Research Flags

Needs deeper research during planning:
- **Phase 3:** S3 Vectors boto3 client availability on ARM64 Lambda; Pinecone vs S3 Vectors tradeoff if third-party constraint is enforced; Lambda deployment package size with llama-index-core + pymupdf + pinecone combined
- **Phase 4:** LlamaIndex + Bedrock Titan Embeddings V2 integration; Pinecone metadata filter syntax for week scoping; Lambda Function URL streaming SAM configuration; Mangum streaming compatibility (may need to bypass Mangum for chat endpoint)

Standard patterns, skip research:
- **Phase 2:** Cognito + API Gateway JWT Authorizer — well-documented AWS pattern
- **Phase 5:** Bedrock structured output via tool use — documented in Claude API docs
- **Phase 6:** Provisioned Concurrency configuration — standard SAM pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core auth and PDF extraction choices are HIGH (PyJWT, pwdlib, pymupdf sourced from FastAPI's own PRs and official docs). Pinecone vs S3 Vectors is a judgment call — neither is a clear winner; Pinecone costs $0 at MVP, S3 Vectors is AWS-native. LlamaIndex vs LangChain benchmark is MEDIUM (single source). |
| Features | MEDIUM | Core feature set is well-grounded in competitor analysis and educational RAG literature. UX thresholds (citation importance, feedback speed) sourced from industry surveys. Multi-course deferral is an opinionated call, not empirically validated. |
| Architecture | MEDIUM-HIGH | Async ingestion pattern and Cognito + API Gateway authorizer are well-documented AWS patterns (HIGH). S3 Vectors is new (GA Dec 2025) — API specifics need validation against actual boto3 version in Lambda. Lambda streaming with Mangum requires investigation. |
| Pitfalls | HIGH | Pitfalls 2 (JSON parse crash) and 3 (open endpoints) are confirmed from direct codebase inspection. Pitfalls 1, 4, 5 are supported by multiple independent sources on RAG failure modes. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Pinecone vs S3 Vectors final decision:** If the "AWS-only" constraint is interpreted strictly, S3 Vectors replaces Pinecone. S3 Vectors pricing at MVP scale needs validation (it is new and pricing details were partially unavailable during research). Decide in Phase 3 planning.
- **Lambda package size:** llama-index-core (~50 MB) + pymupdf + pinecone combined may approach the 250 MB Lambda deployment limit. Validate with `sam build --use-container` before committing to LlamaIndex; fall back to vanilla boto3 chunking if size is a hard constraint.
- **Mangum + streaming compatibility:** Mangum does not natively support Lambda response streaming. The chat endpoint may need to be exposed via a Lambda Function URL that bypasses API Gateway and Mangum entirely for that one route. Confirm this pattern during Phase 4 planning.
- **Bedrock rate limits:** New AWS accounts have ~100 Bedrock invocations/minute. At 5+ concurrent users uploading materials, the EmbedProcessorLambda will hit limits. Request quota increases during Phase 3 before any user testing.
- **Chunking strategy for slides:** Research recommends page-boundary chunking for PDFs (not fixed-size), but image-heavy slides may produce empty text chunks. Need a fallback strategy (skip empty chunks, log for debugging) and empirical validation on real lecture slide PDFs.

## Sources

### Primary (HIGH confidence)
- [Amazon Titan Text Embeddings V2 — AWS Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html) — embedding specs, dimension options, token limits
- [OpenSearch Serverless Pricing — AWS](https://aws.amazon.com/opensearch-service/pricing/) — $174/month minimum confirmed
- [Pinecone Pricing — Starter tier](https://www.pinecone.io/pricing/) — free tier specs
- [FastAPI PR #13917 — migrate to pwdlib/Argon2](https://github.com/fastapi/fastapi/pull/13917) — passlib replacement recommendation
- [FastAPI discussions #11773](https://github.com/fastapi/fastapi/discussions/11773) — Python 3.13 passlib breakage confirmed
- [S3 Vectors Official Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html) — API specs
- [API Gateway + Cognito Authorizer — AWS Docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html) — auth pattern
- [Structured outputs — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — Bedrock tool use for JSON
- Codebase analysis: `.planning/codebase/CONCERNS.md` (2026-03-13) — confirmed existing bugs (JSON parse, open endpoints)

### Secondary (MEDIUM confidence)
- [LangChain vs LlamaIndex 2025 — Latenode](https://latenode.com/blog/langchain-vs-llamaindex-2025-complete-rag-framework-comparison) — retrieval accuracy benchmarks
- [Chunking benchmark Feb 2026 — LangCopilot](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide) — recursive 512-token splitting ranked first
- [6 NotebookLM features for students — Google Blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/) — competitor feature analysis
- [RAG Chatbots for Education — ResearchGate](https://www.researchgate.net/publication/390700272_Retrieval-Augmented_Generation_RAG_Chatbots_for_Education_A_Survey_of_Applications) — educational RAG patterns
- [23 RAG Pitfalls and How to Fix Them — NB Data](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them) — RAG failure modes
- [Serverless RAG Pipeline on AWS — freeCodeCamp](https://www.freecodecamp.org/news/how-to-build-a-serverless-rag-pipeline-on-aws-that-scales-to-zero/) — async ingestion pattern

### Tertiary (LOW confidence)
- [Why we choose against AWS Bedrock Knowledge Bases — Collaborne](https://medium.com/collaborne-engineering/why-we-choose-against-aws-bedrock-knowledge-bases-056d354087af) — user isolation issues with Bedrock Knowledge Bases (single practitioner source; directionally correct, needs validation)
- [Building Serverless RAG on AWS — Loka Engineering Jan 2026](https://medium.com/loka-engineering/building-rag-systems-on-aws-lessons-from-serverless-and-ec2-benchmarks-165b481a0c95) — benchmarks (403 on fetch; citation from search snippet only)

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
