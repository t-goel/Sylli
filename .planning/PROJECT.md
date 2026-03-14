# Sylli AI

## What This Is

Sylli AI is a student-centric RAG study application with a "Syllabus-First" ingestion engine. Students upload their course syllabus and materials (slides, notes, readings), which are automatically organized into a chronological timeline by unit/week. It provides three pillars: a chronological library navigator, a contextual AI tutor with citations, and a quiz generator scoped to any unit or the full course.

## Core Value

Students can upload their course materials and study effectively through an AI that understands their course structure and timeline — not just a generic chat-with-PDF tool.

## Requirements

### Validated

- ✓ Syllabus PDF upload to S3 with Bedrock parsing → week_map extracted and stored in DynamoDB — existing
- ✓ Syllabus retrieval by ID from DynamoDB — existing
- ✓ AWS infrastructure (Lambda, S3, DynamoDB, API Gateway) via SAM CloudFormation — existing

### Active

- [ ] Simple auth — basic login so each student's course is private
- [ ] Material upload — lecture slides, PDFs, notes linked to a syllabus
- [ ] Auto-categorization — AI suggests unit/week assignment for each upload, student confirms or corrects
- [ ] Library navigator — chronological view of all materials organized by syllabus unit/week
- [ ] RAG pipeline — embed uploaded materials, enable semantic retrieval across course content
- [ ] AI tutor — week-aware chat with cross-material context and source citations
- [ ] Quiz generator — generate questions scoped to a unit or the full course

### Out of Scope

- Multi-course support — one active course per user at MVP; adds significant data model complexity
- Adaptive difficulty / performance tracking — quiz is generate-on-demand only for MVP
- OAuth / SSO — simple auth sufficient for MVP
- Mobile app — web-first

## Context

- Backend: Python 3.13, FastAPI + Mangum on AWS Lambda (ARM64), deployed via AWS SAM
- AWS services: API Gateway, S3 (file storage), DynamoDB (metadata), Bedrock (Claude 3.5 Sonnet)
- Frontend: Next.js — to be built from scratch
- Auth: Currently not implemented — all routes are open endpoints
- Syllabus parsing returns a structured `week_map` JSON from Bedrock (unit → topics/readings)
- The Lambda function name in SAM is `HelloWorldFunction` — should be renamed during cleanup

## Constraints

- **Tech stack**: AWS-only backend — no other cloud providers for MVP
- **Auth scope**: Simple email/password login for MVP
- **Single course**: One course per user at MVP
- **Lambda timeout**: 30s — RAG queries and quiz generation must stay within this limit

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| AWS Bedrock (Claude 3.5 Sonnet) for LLM | Already integrated, consistent with AWS-only stack | — Pending |
| Next.js for frontend | SSR benefits for auth + routing, good file upload support | — Pending |
| Syllabus-first architecture | Forces course structure before content upload | — Pending |
| DynamoDB for metadata | Already provisioned, fits key-value access pattern | — Pending |

---
*Last updated: 2026-03-14 after initialization*
