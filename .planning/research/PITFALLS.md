# Pitfalls Research

**Domain:** RAG-based study application on AWS Lambda + Bedrock + DynamoDB + S3
**Researched:** 2026-03-14
**Confidence:** HIGH (existing codebase analysis) / MEDIUM (RAG domain patterns, verified via multiple sources)

---

## Critical Pitfalls

### Pitfall 1: Synchronous Bedrock Calls Hitting the Lambda 30s Timeout

**What goes wrong:**
The Lambda handler waits synchronously for `bedrock.converse()` to return before responding. Syllabus parsing, RAG query answering, and quiz generation all make this call. Any of them can silently exceed the 30s Lambda timeout — the function terminates mid-execution with no partial result saved, the S3 object is orphaned, and the user sees a cold 500 or gateway timeout.

**Why it happens:**
Lambda's synchronous request-response model feels natural during development where PDFs are small and Bedrock responds in 3-8 seconds. Under real conditions — 40-page syllabus, dense lecture slides, multi-unit quiz — Bedrock can take 20-40s. The existing code has no timeout set on the `bedrock.converse()` call (confirmed in `backend/services/bedrock_service.py` line 30), so there is no upper bound other than the Lambda timeout itself.

**How to avoid:**
- Move all Bedrock-heavy operations to an async pattern: upload/request returns `202 Accepted` with a job ID stored in DynamoDB; a second Lambda (triggered by S3 event or SQS) processes the work; client polls a `/jobs/{id}` status endpoint.
- Until async pattern is implemented, set an explicit botocore client timeout of 25s (`connect_timeout=5, read_timeout=25`) so failure is controlled and the error can be logged before Lambda terminates.
- Increase Lambda timeout to 60s for processing functions; keep API-facing functions at 30s.
- Do not extend the quiz generation Lambda timeout as a substitute for the async approach — it is a dead end beyond ~3 units.

**Warning signs:**
- CloudWatch logs show Lambda invocations ending with "Task timed out after 30.00 seconds" rather than a handled exception.
- Users report uploads that "hang" before returning an error.
- Bedrock invocation duration metrics in CloudWatch approach 25s regularly.

**Phase to address:** Foundation / Hardening phase — before any new Bedrock-touching feature is added. The async job pattern must be in place before the RAG pipeline phase or it will require an immediate rewrite.

---

### Pitfall 2: LLM JSON Parsing Failures Crashing the Request with No Recovery

**What goes wrong:**
The existing `json.loads(raw_text)` call in `bedrock_service.py` line 56 has no try-catch. Claude returns "ONLY valid JSON" per the system prompt, but in practice the model occasionally wraps output in markdown code fences (` ```json ... ``` `), adds explanatory text before the JSON, or generates invalid JSON when the input PDF is complex or ambiguous. The call raises `json.JSONDecodeError`, which propagates as a 500 with the raw Bedrock error exposed to the client (confirmed security issue in CONCERNS.md).

**Why it happens:**
Instructing Claude to return "only JSON" works most of the time — perhaps 90-95% of cases — which creates false confidence during development. The failure mode is rare but predictable. The model is not constrained at the API level; it is only asked via natural language prompt.

**How to avoid:**
- Wrap all `json.loads()` on Bedrock responses in a try-catch with a fallback regex extraction: if initial parse fails, search for a JSON block between triple backticks and retry parsing on that substring.
- Use Pydantic `BaseModel` with strict mode to validate parsed JSON against the expected schema (`course_name`, `weeks[]`) immediately after parsing. Return a specific error if required fields are missing.
- Consider using Bedrock's tool use (function calling) API instead of free-form text output for structured schemas — tool calls are more reliably formatted than prompted JSON.
- Log the raw Bedrock response on any parse failure for debugging; never surface the raw response to the client.

**Warning signs:**
- Any 500 error from the syllabus upload endpoint in production that is not an S3 or DynamoDB error.
- CloudWatch logs containing `json.JSONDecodeError` or `JSONDecodeError`.
- QA testing with edge-case PDFs (very short syllabi, image-heavy PDFs, non-English course names) triggering failures.

**Phase to address:** Immediate — this is an existing bug. Must be fixed in the Foundation / Tech Debt phase before any new feature ships.

---

### Pitfall 3: No Authentication Means Student Data Is Publicly Accessible

**What goes wrong:**
All existing endpoints (`POST /syllabus`, `GET /syllabus/{id}`) are open to any HTTP client with the API Gateway URL. Any student's uploaded course materials can be retrieved by anyone who knows or guesses a `syllabus_id` (UUID4 — guessable by brute force at scale). When the RAG pipeline, material uploads, and quiz generation are added without auth, every student's notes, slides, and exam-prep quizzes are unprotected.

**Why it happens:**
Auth is deferred during MVP scaffolding because it adds friction. With Lambda + API Gateway, there is no "default" auth layer — it must be explicitly configured. Developers add the happy path first and plan to add auth "before launch," which slips.

**How to avoid:**
- Add auth before the material upload feature is built — not after. Once data is stored without user ownership, retrofitting ownership into the data model and IAM policies is expensive.
- Use Cognito User Pools with an API Gateway JWT Authorizer (not a Lambda authorizer) — this validates tokens before the Lambda is invoked, eliminating a class of attack without writing custom middleware.
- Every DynamoDB item must include a `user_id` partition key component from the first data migration. The data model shape cannot be changed cost-free after content exists.
- Add a FastAPI `Depends()` middleware that verifies the Cognito JWT and injects `user_id` into all route handlers before any protected route is deployed.

**Warning signs:**
- Routes are deployed to production without a Cognito authorizer configured in `template.yaml`.
- DynamoDB schema does not include `user_id` as a partition key element on any table.
- Endpoint URL is sent to a user before an auth test confirms the endpoint rejects unauthenticated requests.

**Phase to address:** Auth phase — must complete before Material Upload phase. The data model decision (user_id as partition key) must be locked in during the auth phase even if upload comes later.

---

### Pitfall 4: Poor Chunking Strategy Makes the RAG Tutor Useless on Real Course Materials

**What goes wrong:**
A naive fixed-size character or token chunker applied to lecture slides and PDFs will split concept explanations across chunk boundaries, embed slides that contain only an image and a title as near-empty chunks, and produce retrieval results that are syntactically relevant but semantically incomplete. The AI tutor returns answers that are technically sourced from the material but miss critical context — e.g., a formula is retrieved but not its derivation, or a definition is retrieved but not its example. Students lose trust in the tutor quickly.

**Why it happens:**
Fixed-size chunking is the "hello world" of RAG. It is easy to implement, appears to work during testing with well-formatted documents, and requires no parsing of document structure. Lecture slides are hostile to fixed chunking: they are structured as bullet points and headers, not flowing prose. A 500-token chunk boundary set for prose will fall mid-slide or mid-concept on presentation PDFs.

**How to avoid:**
- Use semantic or structure-aware chunking: parse PDFs to extract slide/page boundaries and chunk at those boundaries first, then sub-chunk only if a single slide exceeds the embedding model's token limit.
- Attach metadata to every chunk: `syllabus_week`, `unit_name`, `source_file`, `page_number`. Use metadata filters at retrieval time to constrain results to the week the student is studying.
- Store parent chunk references so the tutor can retrieve a larger context window around the matched chunk when generating its answer.
- Evaluate retrieval quality on a representative set of real lecture slides before shipping the tutor — not just clean PDFs.

**Warning signs:**
- Test queries about specific topics from uploaded slides return chunks that contain only headers or bullet fragments.
- Retrieval consistently misses the "right" slide even when the student asks verbatim text from it.
- The tutor cites a source but the cited content does not contain the actual answer.

**Phase to address:** RAG Pipeline phase — chunking strategy must be decided and tested before the AI tutor is built on top of the retrieval layer.

---

### Pitfall 5: Quiz Generation Produces Out-of-Scope or Hallucinated Questions

**What goes wrong:**
The quiz generator asks Bedrock to generate N questions about a unit. Without strict grounding in retrieved content, Claude draws on its training data to fill gaps — producing questions about topics that were never covered in the student's materials, or generating plausible-sounding but incorrect answer distractors. A student studying from a quiz that tests content not in their course (or tests incorrect facts) is worse than no quiz at all.

**Why it happens:**
LLMs are trained on academic content and can confidently generate exam questions about any topic from memory. The model cannot distinguish between "information I know about thermodynamics" and "information from this student's lecture slides" unless retrieval is strictly enforced. Prompt-only constraints ("only use the provided context") are insufficient on their own.

**How to avoid:**
- The quiz generation prompt must include retrieved chunk content as the exclusive source, not the topic name alone. Explicitly instruct the model: "Generate questions only from the following retrieved passages. Do not use outside knowledge."
- Add a post-generation validation step: for each generated question, verify that the correct answer is supported by at least one retrieved chunk (model-graded or keyword match).
- Cap question count at a number that fits within the retrieved context window — do not ask for 20 questions from 3 retrieved chunks.
- Return source references alongside each question so students can verify answers.

**Warning signs:**
- Quiz questions reference authors, studies, or examples not present in the uploaded materials.
- Distractor options are plausible but untestably wrong — no correct answer can be found in the source material.
- Quiz generation works fine for one topic but produces obviously wrong results for niche course topics.

**Phase to address:** Quiz Generator phase — retrieval-grounded generation must be the baseline design, not an afterthought added after initial quiz generation works.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `except Exception as e` catch-all | Prevents unhandled errors | Masks root cause; exposes internal errors to client; impossible to debug specific failures | Never — always catch specific exception types |
| Hardcoded env var defaults in service files | Works without config | Silent wrong-environment behavior; production runs against dev resources if env var missing | Never — fail fast on missing required env vars |
| No boto3 retry config | Simpler client setup | Single transient AWS failure (rate limit, brief outage) crashes user request with no retry | Never — always configure retries for AWS SDK clients |
| Blocking boto3 in async FastAPI handlers | Familiar sync code pattern | Under concurrent load, blocks the event loop; throughput does not improve with concurrency | Acceptable for MVP with low concurrent users; migrate to `aioboto3` before scaling |
| Pinning no library versions in requirements.txt | Always gets latest | CI/CD can deploy a broken major version; non-reproducible builds | Never — pin major.minor at minimum |
| Storing raw Bedrock response bytes in S3 without size limit | Simple implementation | DDoS vector; memory exhaustion on large PDFs; unbounded cost | Only in prototype; add size limits before any external users |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Bedrock `converse()` | No timeout set; Lambda timeout terminates mid-call silently | Set `botocore.config.Config(connect_timeout=5, read_timeout=25)`; add explicit timeout shorter than Lambda limit |
| Bedrock JSON output | Trusting prompt instruction to return "ONLY JSON"; no parse fallback | Always add try-catch with markdown code fence extraction fallback + Pydantic schema validation |
| Bedrock model IDs | Hardcoding model ID in source; no env var override | Read from `BEDROCK_MODEL_ID` env var; fail fast if missing; document end-of-life dates |
| Cognito + API Gateway | Adding a Lambda authorizer when a native JWT Authorizer suffices | Use API Gateway `AWS_COGNITO_USER_POOLS` authorizer type — token validation happens before Lambda invocation, reducing cost and latency |
| Cognito + FastAPI | Validating JWT twice (API Gateway + FastAPI middleware) | Trust the API Gateway authorizer; extract `user_id` from the pre-validated `requestContext` instead of re-validating |
| S3 file upload | Reading entire file into Lambda memory before uploading | Stream directly to S3 using multipart upload for files >5 MB; return early if file exceeds size limit |
| DynamoDB | No schema validation before storing Bedrock output | Validate with Pydantic before `put_item`; any structural change in Bedrock output must be caught at the application layer, not discovered from corrupted records |
| Bedrock Embeddings | Using a general-purpose embedding model without testing on academic content | Test retrieval precision on real lecture slide PDFs before committing to an embedding model; cosine similarity thresholds differ by domain |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous Bedrock per-request | Upload/query hangs; Lambda timeouts; gateway 504s | Async job pattern with SQS trigger and polling | At first complex PDF or concurrent user |
| Entire PDF read into Lambda memory | Memory errors on large files; slow uploads | Stream to S3; validate size before reading | PDFs > ~100 MB with 128 MB Lambda memory |
| Cold start on first student request | First request after idle takes 3-8s extra | Provisioned concurrency for API Lambda; SnapStart consideration | Every cold start; noticeable when Lambda is idle for 15+ minutes |
| Fixed-size chunking for embedding | High retrieval noise; wrong chunks returned | Semantic or structure-aware chunking; metadata filters | At any scale with diverse academic content |
| Fetching all DynamoDB items without limit | Scan latency grows with data; no pagination | Always use `limit` + `exclusive_start_key` for list endpoints | At ~1,000+ items per student |
| Generating embeddings synchronously during upload | Upload endpoint feels slow; timeout risk for large files | Decouple upload from embedding with an async job; store embeddings in background | At files > ~20 pages |
| No Bedrock rate limit handling | 429 errors when multiple students upload simultaneously | Exponential backoff retry in boto3 config; default ~100 requests/minute for new AWS accounts | At ~5+ concurrent users without quota increase |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Open API endpoints with no auth | Anyone can read any student's course materials; anyone can upload unlimited files at AWS cost | Add Cognito JWT Authorizer at API Gateway level before any external user touches the system |
| `bedrock:InvokeModel` on `*` resource | Accidental or malicious invocation of any Bedrock model in the account; no cost guardrail | Restrict IAM to specific model ARN pattern: `arn:aws:bedrock:*::foundation-model/anthropic.claude-*` |
| Raw Bedrock/internal errors returned to client | Internal system structure leaked; error messages aid attackers | Log full error server-side; return only a generic message and a correlation ID to the client |
| PDF validated only by file extension | Malicious or corrupted files processed by Bedrock; potential DDoS via giant files | Validate magic bytes (`%PDF` header); enforce max file size (e.g., 25 MB) before reading content |
| No S3 public access block | Misconfiguration in a future infra change could expose student materials publicly | Add `PublicAccessBlockConfiguration` with all flags true; enable server-side encryption (SSE-S3 minimum) |
| No ownership check on resource access | Student A can access Student B's syllabus/materials if they know the ID | All DynamoDB queries must include `user_id` in the key condition; never query by `id` alone |
| Student materials stored without isolation | Data leak between users if access control is misconfigured | Namespace S3 object keys by `user_id/`: `{user_id}/{syllabus_id}/{filename}` |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Synchronous upload with no progress feedback | Upload "hangs" for 10-30s; student refreshes, re-uploads, creates duplicate records | Show progress indicator immediately; return job ID; poll `/jobs/{id}` for status |
| Syllabus parsing fails silently (500 returned) | Student does not know if their syllabus was saved; retry creates duplicates | Store job state (`pending`, `processing`, `done`, `failed`) in DynamoDB; surface status in UI with a clear retry button |
| Auto-categorization forces a unit assignment | Student uploads a file, AI assigns it to the wrong week; student cannot easily correct it | Always require student confirmation of unit assignment; make correction a one-click action |
| Quiz generated without scope indication | Student gets quiz questions they cannot trace back to their materials | Show source reference (file + page) for every quiz question and answer; allow student to view the source chunk |
| AI tutor gives an answer with no citation | Student cannot verify the answer; loses trust if it seems wrong | Every tutor response must include inline citations to specific source files and page numbers |
| Cold start delay on first query with no feedback | First question takes 5-10s; student thinks the app is broken | Show a "warming up..." indicator; implement provisioned concurrency for the tutor Lambda |

---

## "Looks Done But Isn't" Checklist

- [ ] **Syllabus upload:** Bedrock call succeeds in local dev but times out on 20+ page PDFs in Lambda — verify with a real-length syllabus in a deployed environment, not just locally.
- [ ] **Auth integration:** Cognito authorizer is configured in `template.yaml` AND tested with an invalid token — verify the API returns 401 (not 200 or 500) on bad tokens.
- [ ] **Data ownership:** DynamoDB queries for syllabi and materials include `user_id` in the filter — verify one user cannot retrieve another user's records by ID alone.
- [ ] **RAG retrieval:** Embedding pipeline produces non-empty vectors for slide-heavy PDFs (image-dominant slides may produce empty text) — verify retrieval returns meaningful chunks for a test query.
- [ ] **Quiz generation:** Questions are grounded in retrieved content, not training data — verify with a niche topic that only exists in the uploaded material, not in common academic texts.
- [ ] **Error handling:** Bedrock JSON parse failure returns a 4xx/5xx with a clean message and does NOT expose raw model output — verify by sending a corrupted or minimal PDF.
- [ ] **File validation:** Magic byte check rejects a `.pdf` file that is actually a text file — verify rejection of a renamed `.txt` file.
- [ ] **Cold start:** First Lambda invocation after 15 minutes of idle returns a result (not a timeout or gateway error) — verify with a staged cold start test.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Lambda timeout in production with no async job pattern | HIGH | Implement async job pattern (SQS + polling endpoint); re-process any orphaned S3 uploads from CloudWatch logs |
| Auth added after data exists without user_id in schema | HIGH | Migration script to assign all existing records to a default/admin user; DynamoDB table may need recreation if partition key changes |
| Bedrock JSON parse crash in production | LOW | Deploy parse fallback + Pydantic validation in a single patch; run re-parse job on any syllabus_id with no `week_map` in DynamoDB |
| Chunking strategy producing poor retrieval | MEDIUM | Re-chunk and re-embed all uploaded materials; vector store must be cleared and repopulated; requires a backfill job |
| Student materials publicly accessible (S3 misconfiguration) | HIGH | Immediate: enable public access block; audit CloudTrail for unauthorized access; notify affected users per FERPA obligations |
| Quiz generating hallucinated questions | MEDIUM | Update generation prompt + add retrieval grounding; existing quizzes cannot be retroactively corrected but future generation is fixed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Lambda 30s timeout (sync Bedrock) | Foundation / Hardening | CloudWatch shows no timeout errors on 20-page PDF upload; job status polling returns `done` within 60s |
| Bedrock JSON parse crash | Foundation / Tech Debt (immediate) | Unit tests covering malformed JSON, markdown-wrapped JSON, missing fields all pass; 500s on syllabus upload drop to zero |
| No authentication / open endpoints | Auth Phase (before Material Upload) | API Gateway returns 401 for all requests without a valid Cognito JWT; `user_id` is present in all DynamoDB records |
| Poor chunking / low RAG quality | RAG Pipeline Phase | Retrieval precision test: >80% of queries return a chunk from the correct unit; no empty-text chunks in vector store |
| Quiz hallucination / out-of-scope questions | Quiz Generator Phase | Manual review of 20 generated questions: zero questions reference content not present in uploaded materials |
| Missing data ownership checks | Auth Phase | Integration test: authenticated user A cannot retrieve user B's syllabus_id; 403 returned, not 200 or 404 |
| Cold starts impacting UX | Infrastructure / Polish Phase | P95 first-request latency < 3s after provisioned concurrency configured |
| No structured logging / observability | Foundation / Hardening | Every Bedrock call, S3 operation, and DynamoDB write emits a structured JSON log line with `request_id`, `user_id`, duration |

---

## Sources

- Codebase analysis: `/Users/tanmaygoel/CS/Sylli/.planning/codebase/CONCERNS.md` (2026-03-13) — HIGH confidence, direct code inspection
- [23 RAG Pitfalls and How to Fix Them](https://www.nb-data.com/p/23-rag-pitfalls-and-how-to-fix-them) — MEDIUM confidence
- [RAG failure modes: common pitfalls and solutions](https://snorkel.ai/blog/retrieval-augmented-generation-rag-failure-modes-and-how-to-fix-them/) — MEDIUM confidence
- [Best Chunking Strategies for RAG (and LLMs) in 2026](https://www.firecrawl.dev/blog/best-chunking-strategies-rag) — MEDIUM confidence
- [Chunking Strategies for RAG: Best Practices — Weaviate](https://weaviate.io/blog/chunking-strategies-for-rag) — MEDIUM confidence
- [AWS Lambda Cold Starts in 2025](https://edgedelta.com/company/knowledge-center/aws-lambda-cold-start-cost) — MEDIUM confidence
- [AWS Lambda Cold Start Optimization — What Actually Works](https://zircon.tech/blog/aws-lambda-cold-start-optimization-in-2025-what-actually-works/) — MEDIUM confidence
- [Structured Outputs with AWS Bedrock and Pydantic — Instructor](https://python.useinstructor.com/integrations/bedrock/) — MEDIUM confidence
- [Structured outputs — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — HIGH confidence
- [Why we choose against AWS Bedrock Knowledge Bases](https://medium.com/collaborne-engineering/why-we-choose-against-aws-bedrock-knowledge-bases-056d354087af) — LOW confidence (single source, practitioner experience)
- [Securing FastAPI with OAuth and AWS Cognito](https://www.cheeyeo.xyz/python/fastapi/web/oauth2/aws/cognito/scope/2025/12/19/fastapi-oauth-cognito-scopes/) — MEDIUM confidence
- [Demystifying AuthN and AuthZ with AWS Cognito, API Gateway, and FastAPI on Lambda](https://medium.com/@mitchelljeremydaw/demystifying-authn-and-authz-with-aws-cognito-api-gateway-and-fastapi-on-lambda-c9d6c6610d16) — MEDIUM confidence

---
*Pitfalls research for: RAG study application — AWS Lambda + Bedrock + DynamoDB + S3*
*Researched: 2026-03-14*
