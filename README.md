# Sylli AI

A student-centric RAG study application with a **Syllabus-First** ingestion engine. Upload your course syllabus and materials — Sylli organizes everything into a chronological timeline by unit/week, then gives you an AI tutor that understands your course structure and a quiz generator scoped to any unit.

## Features

- **Syllabus-first ingestion** — upload your syllabus PDF; Bedrock (Claude 3.5 Sonnet) extracts a structured `week_map` organizing the course by unit/topic
- **Material upload** — attach lecture slides, PDFs, and notes; AI auto-suggests the unit assignment for each file
- **Library navigator** — chronological view of all materials organized by syllabus unit/week
- **AI tutor** — week-aware chat with cross-material RAG context and source citations
- **Quiz generator** — generate questions scoped to a specific unit or the full course
- **Auth** — email/password login so each student's course stays private

## Architecture

```
frontend/          Next.js 16 + TypeScript + Tailwind CSS
backend/           FastAPI + Mangum → AWS Lambda (Python 3.13, ARM64)
template.yaml      AWS SAM CloudFormation (Lambda, API Gateway, S3, DynamoDB)
```

**AWS services:** API Gateway · S3 (syllabus + materials storage) · DynamoDB (metadata) · Bedrock (embeddings + LLM) · Lambda (main API + async embed worker)

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Python 3.13
- Node.js 20+

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Development

### Run the frontend locally

```bash
cd frontend
npm run dev
# http://localhost:3000
```

### Run the backend locally (SAM)

```bash
sam build
sam local start-api
```

### Deploy to AWS

```bash
sam build
sam deploy --guided
```

## Environment Variables

The SAM template injects these automatically. For local development, set them in your environment or a `.env` file:

| Variable | Description |
|---|---|
| `SYLLABUS_BUCKET` | S3 bucket for syllabus PDFs |
| `SYLLABUS_TABLE` | DynamoDB table for syllabus metadata |
| `USERS_TABLE` | DynamoDB table for user accounts |
| `JWT_SECRET` | Secret key for JWT signing |
| `MATERIALS_BUCKET` | S3 bucket for uploaded materials |
| `MATERIALS_TABLE` | DynamoDB table for material metadata |
| `EMBED_FUNCTION_NAME` | ARN of the async embedding Lambda |
| `VECTOR_BUCKET_NAME` | S3 Vectors bucket name |
| `VECTOR_INDEX_NAME` | S3 Vectors index name |

## API

All routes are prefixed with `/api/v1`.

| Router | Prefix | Description |
|---|---|---|
| `health` | `/api/v1/health` | Health check |
| `auth` | `/api/v1/auth` | Register / login |
| `syllabus` | `/api/v1/syllabus` | Syllabus upload and retrieval |
| `materials` | `/api/v1/materials` | Material upload and management |
| `tutor` | `/api/v1/tutor` | AI tutor chat |
| `quiz` | `/api/v1/quiz` | Quiz generation |

## Testing

```bash
cd backend
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE)
