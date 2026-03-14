# Sylli — Technical Specification

**Version:** 1.0
**Last Updated:** 2026-03-13
**Status:** In Development (Phase 1 Complete)

---

## 1. System Overview

Sylli is a Retrieval-Augmented Generation (RAG) study application that uses a "Syllabus-First" ingestion engine to auto-categorize course materials into a chronological timeline and provide contextual AI tutoring and quiz generation. The system is fully serverless on AWS.

### Architecture Diagram (Logical)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (React/Next.js)                     │
│  ┌──────────────┐  ┌───────────────────┐  ┌──────────────────────┐ │
│  │  Navigator    │  │  Document Viewer   │  │  Tutor / Examiner   │ │
│  │  (Left 20%)   │  │  (Center 50%)      │  │  (Right 30%)        │ │
│  └──────────────┘  └───────────────────┘  └──────────────────────┘ │
│                         AWS Amplify                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Amazon API Gateway                            │
│                       /api/v1/{proxy+}                              │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│              AWS Lambda (Python 3.13 / ARM64 / FastAPI)             │
│  ┌──────────┐  ┌──────────────┐  ┌────────┐  ┌──────────────────┐ │
│  │ Syllabus │  │  Documents   │  │ Tutor  │  │    Examiner      │ │
│  │ Router   │  │  Router      │  │ Router │  │    Router        │ │
│  └────┬─────┘  └──────┬───────┘  └───┬────┘  └───────┬──────────┘ │
│       │               │              │                │            │
│  ┌────┴───────────────┴──────────────┴────────────────┴──────────┐ │
│  │                     Service Layer                              │ │
│  │  syllabus_service · document_service · tutor_service · quiz   │ │
│  └───────┬──────────────┬──────────────────┬─────────────────────┘ │
│          │              │                  │                        │
│  ┌───────┴───┐  ┌───────┴──────┐  ┌───────┴───────────┐           │
│  │ dynamo    │  │ bedrock      │  │ knowledge_base     │           │
│  │ _service  │  │ _service     │  │ _service           │           │
│  └───────────┘  └──────────────┘  └───────────────────┘           │
└────────┬──────────────┬──────────────────┬─────────────────────────┘
         │              │                  │
         ▼              ▼                  ▼
   ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐
   │ DynamoDB │  │ Bedrock  │  │ Bedrock Knowledge Bases      │
   │          │  │ (Claude) │  │ (Titan Embeddings +           │
   │          │  │          │  │  OpenSearch Serverless)        │
   └──────────┘  └──────────┘  └──────────────────────────────┘
                                         ▲
         ┌───────────┐                   │
         │    S3     │───── EventBridge ──┘
         │  Bucket   │   (on file upload)
         └───────────┘
```

---

## 2. Current Implementation Status

| Component | Status | Notes |
|:---|:---|:---|
| SAM IaC (Lambda, API GW, S3, DynamoDB) | **Done** | `template.yaml` fully configured |
| Health endpoint | **Done** | `GET /api/v1/health` |
| Syllabus upload + Bedrock parsing | **Done** | `POST /api/v1/syllabus` |
| Syllabus retrieval | **Done** | `GET /api/v1/syllabus/{id}` |
| Document upload + auto-tagging | Not started | |
| Bedrock Knowledge Bases (RAG) | Not started | |
| Tutor chat endpoint | Not started | |
| Quiz generation endpoint | Not started | |
| Frontend UI | Not started | |
| Authentication | Not started | |
| EventBridge triggers | Not started | |

---

## 3. Infrastructure

### 3.1 AWS Resources (SAM / CloudFormation)

| Resource | Logical ID | Config |
|:---|:---|:---|
| Lambda | `SylliFunction` | Runtime: Python 3.13, Arch: ARM64, Timeout: 30s, Handler: `backend/app.lambda_handler` |
| API Gateway | (implicit from SAM `Api` event) | Route: `/{proxy+}`, Method: `ANY` |
| S3 Bucket | `SyllabusBucket` | Name: `sylli-syllabus-bucket` |
| DynamoDB Table | `SyllabusTable` | Name: `sylli-syllabus-table`, Key: `syllabus_id (S)`, Billing: PAY_PER_REQUEST |
| CloudWatch | `ApplicationResourceGroup` + `ApplicationInsightsMonitoring` | Auto-configured |

### 3.2 IAM Permissions

- `S3ReadPolicy` + `S3WritePolicy` on `sylli-syllabus-bucket`
- `DynamoDBReadPolicy` + `DynamoDBWritePolicy` on `sylli-syllabus-table`
- `bedrock:InvokeModel` on `*`

### 3.3 Environment Variables (Lambda)

| Variable | Value |
|:---|:---|
| `SYLLABUS_BUCKET` | `sylli-syllabus-bucket` |
| `SYLLABUS_TABLE` | `sylli-syllabus-table` |

### 3.4 Region & Deployment

- **Region:** `us-east-1`
- **Stack Name:** `Sylli`
- **Build:** SAM CLI with caching + parallel builds
- **Local Dev:** Warm containers (EAGER mode)

---

## 4. Backend API Specification

### 4.1 Existing Endpoints

#### `GET /api/v1/health`
Health check / liveness probe.

**Response** `200`:
```json
{ "status": "ok" }
```

---

#### `POST /api/v1/syllabus`
Upload a syllabus PDF. The system stores it in S3, sends it to Bedrock (Claude 3.5 Sonnet) for parsing, and persists the extracted week map in DynamoDB.

**Request:** `multipart/form-data`
| Field | Type | Required | Constraints |
|:---|:---|:---|:---|
| `file` | File (PDF) | Yes | Must be `application/pdf` |

**Response** `200`:
```json
{
  "syllabus_id": "uuid",
  "filename": "course_syllabus.pdf",
  "week_map": {
    "course_name": "Introduction to Psychology",
    "weeks": [
      {
        "week": 1,
        "topic": "History of Psychology",
        "readings": ["Chapter 1: Origins"],
        "notes": "Focus on Wundt and James"
      }
    ]
  }
}
```

**Errors:**
| Code | Condition |
|:---|:---|
| `400` | File is not a PDF |
| `500` | Bedrock / S3 / DynamoDB failure |

---

#### `GET /api/v1/syllabus/{syllabus_id}`
Retrieve a previously parsed syllabus by ID.

**Response** `200`:
```json
{
  "syllabus_id": "uuid",
  "filename": "course_syllabus.pdf",
  "s3_key": "syllabus/{id}/{filename}",
  "week_map": { ... },
  "uploaded_at": "2026-03-02T12:00:00Z"
}
```

**Errors:**
| Code | Condition |
|:---|:---|
| `404` | Syllabus ID not found |

---

### 4.2 Planned Endpoints

#### `POST /api/v1/syllabus/{syllabus_id}/documents`
Upload a course document (slides, readings, notes). The system auto-tags it to a week/topic using the syllabus week map.

**Request:** `multipart/form-data`
| Field | Type | Required | Constraints |
|:---|:---|:---|:---|
| `file` | File | Yes | PDF, PPTX, DOCX, or image |

**Response** `200`:
```json
{
  "document_id": "uuid",
  "filename": "lecture_3_slides.pdf",
  "s3_key": "documents/{syllabus_id}/{document_id}/{filename}",
  "auto_tag": {
    "week": 3,
    "topic": "The French Revolution",
    "confidence": 0.92
  },
  "summary": "AI-generated 2-3 sentence TL;DR"
}
```

---

#### `GET /api/v1/syllabus/{syllabus_id}/documents`
List all documents for a syllabus, grouped by week.

**Response** `200`:
```json
{
  "syllabus_id": "uuid",
  "documents": [
    {
      "document_id": "uuid",
      "filename": "lecture_3_slides.pdf",
      "week": 3,
      "topic": "The French Revolution",
      "summary": "...",
      "uploaded_at": "2026-03-10T14:00:00Z"
    }
  ]
}
```

---

#### `POST /api/v1/syllabus/{syllabus_id}/chat`
Ask the AI tutor a question grounded in uploaded course materials (RAG).

**Request:**
```json
{
  "message": "What were the main causes of the French Revolution?",
  "week_scope": [3, 4],          // optional: limit to specific weeks
  "conversation_id": "uuid"      // optional: continue a conversation
}
```

**Response** `200`:
```json
{
  "conversation_id": "uuid",
  "answer": "Based on your course materials, the main causes...",
  "citations": [
    {
      "document_id": "uuid",
      "filename": "chapter_5_revolution.pdf",
      "page": 12,
      "snippet": "The fiscal crisis of 1789..."
    }
  ]
}
```

---

#### `POST /api/v1/syllabus/{syllabus_id}/quiz`
Generate a quiz scoped to selected weeks/units.

**Request:**
```json
{
  "weeks": [1, 2, 3, 4, 5, 6],
  "question_count": 15,
  "question_types": ["multiple_choice", "short_answer", "matching", "essay"]
}
```

**Response** `200`:
```json
{
  "quiz_id": "uuid",
  "title": "Midterm Review: Weeks 1-6",
  "questions": [
    {
      "id": 1,
      "type": "multiple_choice",
      "question": "Which philosopher is considered the founder of experimental psychology?",
      "options": ["Freud", "Wundt", "James", "Pavlov"],
      "correct_answer": "Wundt",
      "explanation": "Wilhelm Wundt established the first psychology lab in 1879.",
      "source": { "document_id": "uuid", "page": 5 }
    },
    {
      "id": 2,
      "type": "short_answer",
      "question": "Explain the difference between structuralism and functionalism.",
      "rubric": "Should mention Titchener (structuralism) and James (functionalism)...",
      "source": { "document_id": "uuid", "page": 8 }
    }
  ]
}
```

---

#### `POST /api/v1/syllabus/{syllabus_id}/quiz/{quiz_id}/submit`
Submit quiz answers for AI grading.

**Request:**
```json
{
  "answers": [
    { "question_id": 1, "answer": "Wundt" },
    { "question_id": 2, "answer": "Structuralism focused on breaking down..." }
  ]
}
```

**Response** `200`:
```json
{
  "score": 13,
  "total": 15,
  "percentage": 86.7,
  "results": [
    { "question_id": 1, "correct": true },
    { "question_id": 2, "correct": true, "feedback": "Good answer. You could also mention..." }
  ]
}
```

---

## 5. Data Models

### 5.1 DynamoDB Tables

#### `sylli-syllabus-table` (Exists)

| Attribute | Type | Key | Description |
|:---|:---|:---|:---|
| `syllabus_id` | String | PK (Hash) | UUID |
| `filename` | String | | Original filename |
| `s3_key` | String | | S3 object path |
| `week_map` | Map | | Parsed course structure (see schema below) |
| `uploaded_at` | String | | ISO 8601 timestamp |

**`week_map` schema:**
```json
{
  "course_name": "string",
  "weeks": [
    {
      "week": "number",
      "topic": "string",
      "readings": ["string"],
      "notes": "string"
    }
  ]
}
```

#### `sylli-documents-table` (Planned)

| Attribute | Type | Key | Description |
|:---|:---|:---|:---|
| `document_id` | String | PK (Hash) | UUID |
| `syllabus_id` | String | GSI-PK | Links to parent syllabus |
| `filename` | String | | Original filename |
| `s3_key` | String | | S3 object path |
| `week` | Number | GSI-SK | Auto-tagged week number |
| `topic` | String | | Auto-tagged topic |
| `summary` | String | | AI-generated TL;DR |
| `file_type` | String | | pdf, pptx, docx, image |
| `page_count` | Number | | Number of pages |
| `uploaded_at` | String | | ISO 8601 timestamp |

**GSI:** `syllabus-week-index` — PK: `syllabus_id`, SK: `week`

#### `sylli-conversations-table` (Planned)

| Attribute | Type | Key | Description |
|:---|:---|:---|:---|
| `conversation_id` | String | PK (Hash) | UUID |
| `syllabus_id` | String | GSI-PK | Links to parent syllabus |
| `messages` | List | | Chat history `[{role, content, citations, timestamp}]` |
| `created_at` | String | | ISO 8601 timestamp |
| `updated_at` | String | | ISO 8601 timestamp |

#### `sylli-quizzes-table` (Planned)

| Attribute | Type | Key | Description |
|:---|:---|:---|:---|
| `quiz_id` | String | PK (Hash) | UUID |
| `syllabus_id` | String | GSI-PK | Links to parent syllabus |
| `weeks` | List | | Weeks covered |
| `questions` | List | | Full question objects |
| `submissions` | List | | Answer submissions with scores |
| `created_at` | String | | ISO 8601 timestamp |

### 5.2 S3 Object Layout

```
sylli-syllabus-bucket/
├── syllabus/
│   └── {syllabus_id}/
│       └── {filename}.pdf
└── documents/
    └── {syllabus_id}/
        └── {document_id}/
            └── {filename}
```

---

## 6. AI / Bedrock Integration

### 6.1 Syllabus Parsing (Implemented)

- **Model:** `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Input:** Base64-encoded PDF sent as document block
- **System prompt:** Instructs Claude to extract a structured JSON week map with `course_name`, `weeks[]` (each with `week`, `topic`, `readings[]`, `notes`)
- **Max tokens:** 4096
- **Temperature:** Not specified (Bedrock default)

### 6.2 Document Auto-Tagging (Planned)

- **Model:** Claude 3.5 Sonnet via Bedrock
- **Input:** Document content + syllabus week map
- **Output:** Best-match `week`, `topic`, `confidence` score, and 2-3 sentence `summary`
- **Strategy:** Compare document text against week map themes; use cosine similarity as a fallback via embeddings

### 6.3 RAG Pipeline (Planned)

- **Embedding Model:** Amazon Titan Embeddings (via Bedrock Knowledge Bases)
- **Vector Store:** Amazon OpenSearch Serverless
- **Chunking Strategy:** Bedrock Knowledge Bases default (fixed-size with overlap)
- **Data Source:** S3 bucket (`documents/` prefix)
- **Retrieval:** Top-k relevant chunks (k=10-15) per query
- **Generation:** Claude 3.5 Sonnet synthesizes answer from retrieved chunks
- **Citation Tracking:** Each chunk carries `document_id` + `page` metadata for source linking

### 6.4 Quiz Generation (Planned)

- **Model:** Claude 3.5 Sonnet via Bedrock
- **Input:** Retrieved chunks from selected weeks + question type instructions
- **Output:** Structured JSON quiz with questions, options, answers, explanations, and source references
- **Answer Grading:** Claude evaluates free-text answers against rubrics

---

## 7. Frontend Specification

### 7.1 Tech Stack (Planned)

| Layer | Technology |
|:---|:---|
| Framework | React or Next.js (TypeScript) |
| Styling | Tailwind CSS (dark-mode first) |
| State Management | React Context or Zustand |
| PDF Rendering | react-pdf or PDF.js |
| Hosting | AWS Amplify |
| API Client | Fetch / Axios |

### 7.2 Layout

Three-pane persistent dashboard:

```
┌─────────────┬────────────────────────────────┬───────────────────┐
│             │                                │   Tutor Chat      │
│  Navigator  │        Document Viewer         │   ─ ─ ─ ─ ─ ─    │
│   (20%)     │           (50%)                │   Examiner Quiz   │
│             │                                │      (30%)        │
│ ┌─────────┐ │  ┌──────────────────────────┐  │                   │
│ │ Week 1  │ │  │                          │  │  ┌─────────────┐  │
│ │ Week 2  │ │  │     PDF / Slide          │  │  │ Ask me       │  │
│ │ Week 3 ▸│ │  │     Renderer             │  │  │ anything...  │  │
│ │ Week 4  │ │  │                          │  │  └─────────────┘  │
│ │ ...     │ │  │     (with highlight      │  │                   │
│ │         │ │  │      on citation click)   │  │  [Citation 1]    │
│ └─────────┘ │  │                          │  │  [Citation 2]    │
│             │  └──────────────────────────┘  │                   │
│ [+ Upload]  │                                │  [Toggle Mode]    │
└─────────────┴────────────────────────────────┴───────────────────┘
```

### 7.3 Key Views & Interactions

| View | Description |
|:---|:---|
| **Navigator** | Collapsible week/unit tree. Each week shows topic name + document count. Click to expand and see documents with AI summaries. File upload button at bottom. |
| **Document Viewer** | Renders selected PDF/slides. Supports page navigation, zoom, and citation highlighting (scroll to page + yellow highlight on cited text). |
| **Tutor Chat** | Chat interface with message bubbles. Each AI response includes inline citation chips. Clicking a citation scrolls the Document Viewer to the source page. Optional week-scope filter. |
| **Examiner Quiz** | Select weeks via checkboxes → generate quiz. Renders questions one at a time or all at once. Submit for AI grading. Shows score + per-question feedback. |

---

## 8. Event-Driven Pipeline (Planned)

### 8.1 Document Ingestion Flow

```
User uploads file
       │
       ▼
  API Gateway → Lambda
       │
       ├─→ Store raw file in S3 (documents/{syllabus_id}/{doc_id}/{filename})
       │
       ├─→ Send to Bedrock for auto-tagging (compare against week_map)
       │
       ├─→ Save metadata to DynamoDB (sylli-documents-table)
       │
       └─→ Bedrock Knowledge Base automatically indexes new S3 object
            (chunking → Titan embeddings → OpenSearch Serverless)
```

### 8.2 EventBridge (Future Optimization)

For async processing of large files:
- **Event:** S3 `PutObject` on `documents/` prefix
- **Target:** Lambda function for background processing (tagging, summarization)
- **Benefit:** Returns upload response immediately; tagging completes async

---

## 9. Security & Auth (Planned)

| Concern | Approach |
|:---|:---|
| Authentication | Amazon Cognito User Pools (email/password + optional university SSO) |
| Authorization | Cognito JWT tokens validated at API Gateway |
| Multi-tenancy | `user_id` attribute on all DynamoDB items; query filters enforce isolation |
| File validation | MIME type + extension checks; max file size enforced at API Gateway (10 MB default) |
| Data at rest | S3 SSE-S3 encryption; DynamoDB encryption enabled by default |
| Data in transit | HTTPS enforced via API Gateway |
| CORS | Configured at API Gateway level for Amplify domain |

---

## 10. Development Phases

### Phase 1 — Foundation (Complete)
- [x] SAM infrastructure (Lambda, API Gateway, S3, DynamoDB)
- [x] FastAPI backend scaffold with router/service pattern
- [x] Syllabus upload, Bedrock parsing, S3 storage, DynamoDB persistence
- [x] Health check endpoint

### Phase 2 — Document Pipeline
- [ ] `sylli-documents-table` DynamoDB table
- [ ] Document upload endpoint (`POST /api/v1/syllabus/{id}/documents`)
- [ ] Document listing endpoint (`GET /api/v1/syllabus/{id}/documents`)
- [ ] Bedrock auto-tagging service (match documents to weeks)
- [ ] AI summary generation per document
- [ ] S3 `documents/` folder structure

### Phase 3 — RAG & Tutor
- [ ] Bedrock Knowledge Base creation (Titan Embeddings + OpenSearch Serverless)
- [ ] S3 data source sync configuration
- [ ] Knowledge base query service
- [ ] Tutor chat endpoint (`POST /api/v1/syllabus/{id}/chat`)
- [ ] `sylli-conversations-table` DynamoDB table
- [ ] Citation extraction and page-level source tracking

### Phase 4 — Quiz Engine
- [ ] Quiz generation endpoint (`POST /api/v1/syllabus/{id}/quiz`)
- [ ] Week-scoped retrieval for quiz context
- [ ] Multi-format question generation (MC, matching, short answer, essay)
- [ ] Quiz submission + AI grading endpoint
- [ ] `sylli-quizzes-table` DynamoDB table

### Phase 5 — Frontend
- [ ] Project scaffold (React/Next.js + TypeScript + Tailwind)
- [ ] Three-pane layout shell
- [ ] Navigator component (week tree + file list + upload)
- [ ] Document Viewer (PDF rendering + citation highlights)
- [ ] Tutor Chat component (message list + input + citations)
- [ ] Examiner Quiz component (scope selection + question rendering + grading)
- [ ] Dark mode theming
- [ ] AWS Amplify deployment

### Phase 6 — Production Readiness
- [ ] Cognito authentication
- [ ] Multi-user data isolation
- [ ] EventBridge async processing
- [ ] Error monitoring + alerting (CloudWatch)
- [ ] Rate limiting
- [ ] Unit + integration test coverage
- [ ] CI/CD pipeline (GitHub Actions → SAM deploy)

---

## 11. Dependencies

### Backend (`backend/requirements.txt`)

| Package | Purpose |
|:---|:---|
| `fastapi` | Web framework |
| `mangum` | ASGI → Lambda adapter |
| `python-multipart` | File upload parsing |
| `uvicorn` | Local dev server |
| `boto3` | AWS SDK (S3, DynamoDB, Bedrock) |

### Test (`tests/requirements.txt`)

| Package | Purpose |
|:---|:---|
| `pytest` | Test runner |
| `boto3` | AWS SDK for integration tests |
| `requests` | HTTP client for integration tests |

---

## 12. File Structure (Current + Planned)

```
Sylli/
├── backend/
│   ├── app.py                      # FastAPI entry + Mangum handler
│   ├── requirements.txt
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py               # GET /health
│   │   ├── syllabus.py             # POST/GET /syllabus
│   │   ├── documents.py            # (planned) POST/GET /documents
│   │   ├── chat.py                 # (planned) POST /chat
│   │   └── quiz.py                 # (planned) POST /quiz
│   └── services/
│       ├── bedrock_service.py      # Claude invocation
│       ├── dynamo_service.py       # DynamoDB operations
│       ├── syllabus_service.py     # Syllabus business logic
│       ├── document_service.py     # (planned) Document ingestion
│       ├── knowledge_base_service.py # (planned) RAG retrieval
│       ├── tutor_service.py        # (planned) Chat orchestration
│       └── quiz_service.py         # (planned) Quiz gen + grading
├── frontend/                       # (planned) React/Next.js app
├── tests/
│   ├── unit/
│   └── integration/
├── template.yaml                   # SAM IaC
├── samconfig.toml                  # SAM CLI config
├── README.md                       # PRD
└── SPEC.md                         # This document
```
