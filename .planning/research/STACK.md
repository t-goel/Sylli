# Stack Research

**Domain:** RAG-based study application (brownfield — additions to existing FastAPI + AWS Lambda + Bedrock backend)
**Researched:** 2026-03-14
**Confidence:** MEDIUM-HIGH (vector store choice has a cost tradeoff requiring a judgment call)

---

## Existing Stack (Do Not Change)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.13 | Runtime |
| FastAPI | 0.x | API framework |
| Mangum | latest | ASGI → Lambda adapter |
| AWS Lambda | ARM64 | Compute (30s timeout) |
| AWS SAM | latest | IaC / deployment |
| AWS S3 | — | File storage |
| AWS DynamoDB | — | Metadata (syllabus, users) |
| AWS Bedrock (Claude 3.5 Sonnet) | — | LLM for parsing + generation |
| boto3 | latest | AWS SDK |

---

## Recommended Additions

### RAG Pipeline

#### Embeddings

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) | via Bedrock API | Convert text chunks to vectors | Already in the AWS stack; no external account, no egress cost, no new dependency. 1024-dim output (configurable to 256/512), 8192 token input limit, optimized for RAG. Use 512 dims for 33% cost reduction with ~99% accuracy retention. Confidence: HIGH |

Why NOT Cohere Embed / OpenAI Embeddings: Requires separate API accounts and keys outside the AWS-only constraint. Adds cost and operational overhead.

#### Vector Store

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Pinecone Serverless | `pinecone` >= 5.1.0 (v8.x current) | Store and query embedding vectors | True serverless — zero monthly minimum on Starter tier (2 GB, 2M write units, 1M read units/month free). No OCU floor unlike OpenSearch Serverless ($174-350/month minimum). HTTP API fits Lambda cold-start pattern perfectly. Confidence: MEDIUM |

Why NOT OpenSearch Serverless: Minimum $174/month even in dev/test non-redundant mode ($350/month with redundancy). HNSW-only via Faiss. Massive overkill for a single-course-per-user MVP with hundreds, not millions, of vectors.

Why NOT pgvector (RDS): Requires an always-on RDS instance — incompatible with AWS-only serverless constraint and adds ~$15-50/month minimum even for the smallest instance. Lambda to RDS connectivity also requires VPC configuration complexity.

Why NOT FAISS in-memory on Lambda: State is lost between cold starts. Cannot persist vectors across invocations without reading from S3 each time — adds 2-5s overhead per query, and exceeds the 30s timeout risk.

**Pinecone tradeoff to acknowledge:** Pinecone is a third-party SaaS, not AWS-native. The project has an "AWS-only backend" constraint. Pinecone is the pragmatic exception — it is available on AWS Marketplace, targets us-east-1 (same region as the stack), and has zero cost at MVP scale. If the constraint is strict-no-third-party, switch to OpenSearch Serverless and accept the $174/month floor.

#### RAG Orchestration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| LlamaIndex (`llama-index-core`) | 0.14.x (current: 0.14.16) | Chunking, embedding pipeline, retrieval | Purpose-built for document RAG. Better document ingestion pipeline (PDF, slides) than LangChain. Lighter mental model for a pipeline that doesn't need agent orchestration. Confidence: MEDIUM |

Why NOT LangChain: More versatile but more complex. In 2025, community consensus is that LangChain is bloated for straightforward RAG-only workflows. LlamaIndex has 35% better retrieval accuracy benchmarks for document-heavy applications per recent comparisons.

Why NOT raw boto3 with manual chunking: Viable but error-prone. Chunking, overlap, metadata attachment, and retrieval logic are solved problems — don't rebuild them.

#### Text Extraction / Document Processing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `pymupdf` (PyMuPDF) | 1.25.x | PDF text extraction, slide content extraction | Fastest Python PDF extractor (42ms vs 2.5s for pdfminer). Handles layout-sensitive PDFs (lecture slides) better than PyPDF2. Extracts text per page, which maps naturally to chunking by slide. Confidence: HIGH |
| `python-pptx` | 1.x | Extract text from .pptx lecture slides | Students upload PowerPoint slides — this is the only pure-Python library for .pptx text extraction. Confidence: HIGH |

Why NOT PyPDF2: Unmaintained (archived on GitHub). Poor handling of complex layouts / multi-column PDFs.

Why NOT pdfplumber: Good for tables but 3x slower than PyMuPDF for standard extraction. Lambda cold-start budget doesn't support this.

#### Chunking Strategy

Use recursive 512-token splitting with 10-15% overlap (50-75 tokens). A February 2026 benchmark of 7 strategies placed recursive 512-token splitting first at 69% retrieval accuracy. Semantic chunking underperformed (54%) due to fragmentation. Implement via LlamaIndex's `SentenceSplitter` with `chunk_size=512, chunk_overlap=64`.

---

### Authentication

#### Backend (FastAPI on Lambda + DynamoDB)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `PyJWT` | 2.11.x | JWT encode/decode | Actively maintained, lightweight, no compiled dependencies that cause ARM64 Lambda packaging issues. python-jose is effectively unmaintained and has CVEs. Confidence: HIGH |
| `pwdlib[argon2]` | 0.2.x | Password hashing | Passlib is unmaintained and its `crypt` module dependency is removed in Python 3.13 (PEP 594 — this WILL break passlib on the existing runtime). pwdlib is the replacement recommended in FastAPI's own PRs. Argon2 is the modern algorithm over bcrypt. Confidence: HIGH |
| DynamoDB (existing) | — | User credential store | Already provisioned. Add a `users` table (partition key: `email`) storing `email`, `password_hash`, and `user_id`. No new infrastructure. Confidence: HIGH |

Auth flow: `POST /auth/register` + `POST /auth/login` → returns JWT in httpOnly cookie. All protected routes validate via FastAPI `Depends` on a `get_current_user` dependency that decodes the JWT.

Why NOT Amazon Cognito: Adds managed infrastructure, webhook complexity, and a non-trivial learning curve for what is explicitly scoped as "simple email/password login." Cognito is worth it at scale; for MVP with one developer it is over-engineered.

Why NOT python-jose: Last release was 2022, has known CVEs, and depends on the ecdsa library which also has vulnerabilities. PyJWT is the community migration target.

Why NOT passlib: Incompatible with Python 3.13 due to PEP 594 removal of `crypt`. This is a hard blocker on the existing runtime.

#### Frontend (Next.js)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `js-cookie` or native fetch + httpOnly cookies | — | Store and send auth token | FastAPI returns JWT in `Set-Cookie: token=...; HttpOnly; Secure; SameSite=Strict`. Next.js middleware reads the cookie to protect routes. No client-side token storage — eliminates XSS token theft. Confidence: HIGH |
| Next.js Middleware (`middleware.ts`) | built-in | Protect routes server-side | Redirect unauthenticated users before the page renders. Standard Next.js 15 pattern — no additional library needed. Confidence: HIGH |

Why NOT NextAuth / Auth.js: Adds complexity for a backend-issued JWT pattern. NextAuth manages its own session/token layer which conflicts with FastAPI-issued tokens. For an external API backend, rolling simple cookie handling is cleaner.

---

### Frontend

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 15.5 (current) | React framework | Already decided. App Router, React 19, Turbopack dev server, stable Server Actions. Confidence: HIGH |
| TypeScript | 5.x | Type safety | Standard with Next.js 15. Typed routes catch broken links at compile time. |
| Tailwind CSS | 4.x | Styling | v4 is current as of 2025, integrated with Next.js. Zero runtime CSS. Confidence: HIGH |
| shadcn/ui | latest (no version — copy-paste components) | Component library | Standard pairing with Tailwind + Next.js in 2025. Unstyled base via Radix UI primitives. Accessible. Confidence: HIGH |
| TanStack Query (`@tanstack/react-query`) | 5.x | Server state / data fetching | Standard for Next.js apps that talk to an external API (vs Vercel's own data layer). Handles loading/error states, caching, and refetch. Confidence: HIGH |
| React Hook Form + Zod | `react-hook-form` 7.x, `zod` 3.x | Form validation | Standard pairing in 2025 Next.js ecosystem. Zod schema shared between form validation and API response typing. Confidence: HIGH |
| Zustand | 5.x | Client state (auth status, UI state) | Lightweight. For this app, primary use is storing the decoded user session and controlling UI-only state like sidebar open/closed. Confidence: MEDIUM |

---

## Full Additions to Install

### Backend (Python — add to requirements.txt)

```bash
# RAG pipeline
llama-index-core>=0.14.0
llama-index-embeddings-bedrock>=0.3.0   # Bedrock embeddings integration
pinecone>=5.1.0                          # Vector store (package renamed from pinecone-client)
pymupdf>=1.25.0                          # PDF text extraction
python-pptx>=1.0.0                       # PowerPoint text extraction

# Auth
PyJWT>=2.11.0
pwdlib[argon2]>=0.2.0
```

### Frontend (Next.js — new project)

```bash
# Bootstrap
npx create-next-app@latest sylli-frontend --typescript --tailwind --app

# Data fetching + state
npm install @tanstack/react-query zustand

# Forms + validation
npm install react-hook-form zod @hookform/resolvers

# UI components (shadcn CLI installs individually)
npx shadcn@latest init
npx shadcn@latest add button input card dialog ...

# Auth cookie handling (optional helper)
npm install js-cookie
npm install -D @types/js-cookie
```

---

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| Vector store | Pinecone Serverless | OpenSearch Serverless | If "AWS-only, no third-party" constraint is enforced strictly and budget > $174/month |
| Vector store | Pinecone Serverless | FAISS on Lambda (ephemeral) | Never — state does not persist across Lambda invocations |
| Embeddings | Titan Text V2 | Cohere Embed v3 | If multi-language support beyond 100 languages is needed |
| RAG orchestration | LlamaIndex | LangChain | If the project grows into multi-step agent workflows |
| RAG orchestration | LlamaIndex | Vanilla boto3 | If Lambda package size becomes a constraint (llama-index-core is ~50MB) |
| Password hashing | pwdlib[argon2] | bcrypt | If deploying on Python < 3.11 where passlib still works |
| PDF extraction | PyMuPDF | pdfplumber | If table extraction from PDFs becomes a primary need |
| Frontend state | Zustand | Redux Toolkit | If state grows significantly in complexity (unlikely at MVP) |
| Auth management | Custom JWT cookies | NextAuth | If OAuth providers (Google, GitHub) are added post-MVP |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `python-jose` | Unmaintained since 2022, active CVEs, ecdsa dependency vulnerabilities | `PyJWT` |
| `passlib` | `crypt` module dependency removed in Python 3.13 (PEP 594) — hard incompatibility with existing runtime | `pwdlib[argon2]` |
| `PyPDF2` | Archived / unmaintained, poor complex layout support | `pymupdf` |
| OpenSearch Serverless | $174-350/month minimum even at zero usage — cost-prohibitive for MVP | Pinecone Serverless (free tier) |
| FAISS in Lambda memory | Non-persistent across invocations — unusable for a vector store | Pinecone Serverless |
| Amazon Cognito | Over-engineered for simple email/password MVP; adds webhook complexity | Custom JWT with DynamoDB users table |
| NextAuth / Auth.js | Conflicts with FastAPI-issued JWT pattern; adds unnecessary session management layer | httpOnly cookie + Next.js middleware |
| `pinecone-client` (old package name) | Deprecated, no longer maintained, points to old API | `pinecone` >= 5.1.0 |
| LangChain (for RAG only) | Bloated for straight retrieval; community consensus in 2025 is LlamaIndex wins for document RAG | LlamaIndex |

---

## Version Compatibility Notes

| Package | Compatible With | Notes |
|---------|----------------|-------|
| `pwdlib[argon2]` | Python 3.13 | Explicitly designed as the passlib replacement for Python 3.13+ |
| `PyJWT` 2.11.x | Python 3.13, ARM64 Lambda | Pure Python, no compiled deps — packages cleanly for Lambda |
| `pymupdf` 1.25.x | Python 3.13, ARM64 | Includes compiled MuPDF binaries; must use the ARM64 Lambda layer or build with `--platform linux/arm64` in SAM |
| `pinecone` 5.1.x+ | Python 3.10+ | Requires Python >= 3.10 — compatible with 3.13 |
| `llama-index-core` 0.14.x | Python 3.10+ | Requires Python >= 3.10 — compatible with 3.13 |
| Next.js 15.5 | React 19, Node.js 18+ | Turbopack is default dev bundler; production Turbopack builds are beta in 15.5 |
| `@tanstack/react-query` 5.x | React 18+, React 19 | v5 API differs from v4 — use v5 docs, not v4 |

---

## Lambda Packaging Considerations

`pymupdf` ships compiled binaries and must be built for `linux/arm64`. With SAM:

```yaml
# template.yaml — ensure architecture matches build platform
Globals:
  Function:
    Architecture: arm64

# Build using container for compiled deps
sam build --use-container
```

`llama-index-core` is approximately 50 MB. Combined with `pymupdf`, `pinecone`, and existing deps, the Lambda deployment package may approach the 250 MB unzipped limit. Use Lambda layers to separate heavy deps, or use the SAM `Metadata.BuildMethod: python3.13` to let SAM strip unneeded files.

---

## Sources

- [Amazon Titan Text Embeddings V2 — AWS Blog](https://aws.amazon.com/blogs/aws/amazon-titan-text-v2-now-available-in-amazon-bedrock-optimized-for-improving-rag/) — Titan V2 specs and RAG optimization (HIGH confidence)
- [Amazon Bedrock Titan Embeddings Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html) — Token limits, dimension options (HIGH confidence)
- [OpenSearch Serverless Pricing](https://aws.amazon.com/opensearch-service/pricing/) — $174/month minimum confirmed (HIGH confidence)
- [Pinecone Pricing — Starter tier](https://www.pinecone.io/pricing/) — Free tier specs (2 GB, 5 indexes) (HIGH confidence)
- [Pinecone Python SDK — PyPI](https://pypi.org/project/pinecone/) — Package rename from pinecone-client, v8.x current (HIGH confidence)
- [PyJWT docs](https://pyjwt.readthedocs.io/en/latest/) — v2.11.x (HIGH confidence)
- [FastAPI PR #13917 — migrate to pwdlib/Argon2](https://github.com/fastapi/fastapi/pull/13917) — FastAPI's own migration away from passlib (HIGH confidence)
- [passlib incompatibility discussion — FastAPI #11773](https://github.com/fastapi/fastapi/discussions/11773) — Python 3.13 breakage confirmed (HIGH confidence)
- [LlamaIndex Core — PyPI](https://pypi.org/project/llama-index-core/) — v0.14.16 current (HIGH confidence)
- [LangChain vs LlamaIndex 2025 — Latenode](https://latenode.com/blog/langchain-vs-llamaindex-2025-complete-rag-framework-comparison) — Retrieval accuracy benchmarks (MEDIUM confidence — single source)
- [PyMuPDF comparison 2025 — Medium](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257) — Speed benchmarks (MEDIUM confidence)
- [Next.js 15.5 blog](https://nextjs.org/blog/next-15-5) — Feature list and version confirmation (HIGH confidence)
- [Next.js 2025 stack guide — Wisp CMS](https://www.wisp.blog/blog/what-nextjs-tech-stack-to-try-in-2025-a-developers-guide-to-modern-web-development) — Tailwind, shadcn, TanStack community patterns (MEDIUM confidence)
- [Chunking benchmark Feb 2026 — LangCopilot](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide) — Recursive 512-token splitting ranked first (MEDIUM confidence)

---

*Stack research for: Sylli AI — RAG + Auth + Frontend additions to existing FastAPI/Lambda/Bedrock backend*
*Researched: 2026-03-14*
