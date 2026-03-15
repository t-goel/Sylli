---
phase: 03-materials-and-library
plan: "01"
subsystem: infra
tags: [sam, cloudformation, dynamodb, s3, lambda, bedrock, s3vectors, pymupdf, python-pptx]

# Dependency graph
requires:
  - phase: 02-auth-and-syllabus
    provides: existing SylliFunction, SyllabusTable, UsersTable, SyllabusBucket declarations in template.yaml

provides:
  - MaterialsBucket S3 bucket (sylli-materials-bucket)
  - MaterialsTable DynamoDB table with user_id-index GSI (user_id + uploaded_at RANGE key)
  - EmbedWorkerFunction Lambda (workers.embed_worker.lambda_handler, 300s timeout, s3vectors + bedrock IAM)
  - SylliFunction env vars: MATERIALS_BUCKET, MATERIALS_TABLE, EMBED_FUNCTION_NAME
  - SylliFunction IAM: S3 read/write on materials bucket, DynamoDB read/write on materials table, lambda:InvokeFunction on EmbedWorkerFunction
  - requirements.txt: boto3>=1.39.5, PyMuPDF, python-pptx bundled into SAM deployment package

affects:
  - 03-02 (upload endpoint needs MATERIALS_BUCKET, MATERIALS_TABLE, EMBED_FUNCTION_NAME)
  - 03-03 (embed worker handler needs EmbedWorkerFunction + s3vectors IAM)
  - 03-04 (library list endpoint queries user_id-index GSI)

# Tech tracking
tech-stack:
  added: [PyMuPDF, python-pptx, boto3>=1.39.5 (pinned for s3vectors client)]
  patterns:
    - Async Lambda invocation pattern via EMBED_FUNCTION_NAME env var + lambda:InvokeFunction IAM
    - S3 Vectors access via s3vectors:PutVectors IAM action on EmbedWorkerFunction

key-files:
  created: []
  modified:
    - backend/requirements.txt
    - template.yaml

key-decisions:
  - "boto3 pinned >=1.39.5 in requirements.txt — Lambda runtime ships an older boto3 without s3vectors client; must be bundled by SAM"
  - "EmbedWorkerFunction separate Lambda (not SylliFunction) — 300s timeout for embedding work; avoids API Gateway 29s timeout constraint"
  - "MaterialsTable user_id-index GSI declared at creation — DynamoDB GSIs cannot be added after table creation without recreation"
  - "s3vectors:PutVectors on EmbedWorkerFunction only (not SylliFunction) — least-privilege; only embed worker writes vectors"

patterns-established:
  - "Worker Lambda pattern: long-running async tasks delegated via EMBED_FUNCTION_NAME env var + lambda:InvokeFunction"

requirements-completed: [MAT-01, MAT-04, MAT-05]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 3 Plan 01: Materials Infrastructure Summary

**SAM infrastructure for materials pipeline: MaterialsBucket, MaterialsTable with user_id GSI, EmbedWorkerFunction with s3vectors IAM, and three new Python dependencies (boto3>=1.39.5, PyMuPDF, python-pptx) bundled for Lambda**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T06:00:08Z
- **Completed:** 2026-03-15T06:02:08Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Updated requirements.txt replacing unpinned boto3 with boto3>=1.39.5 and adding PyMuPDF + python-pptx for SAM bundling
- Added all materials SAM resources: MaterialsBucket, MaterialsTable (with user_id-index GSI), EmbedWorkerFunction
- Extended SylliFunction with MATERIALS_BUCKET, MATERIALS_TABLE, EMBED_FUNCTION_NAME env vars and corresponding IAM policies

## Task Commits

Each task was committed atomically:

1. **Task 1: Update requirements.txt with Phase 3 dependencies** - `a230966` (chore)
2. **Task 2: Add materials infrastructure to template.yaml** - `4c2c288` (feat)

**Plan metadata:** *(docs commit follows)*

## Files Created/Modified

- `backend/requirements.txt` - Pinned boto3>=1.39.5, added PyMuPDF and python-pptx
- `template.yaml` - Added EmbedWorkerFunction, MaterialsBucket, MaterialsTable with GSI, plus env vars and IAM on SylliFunction

## Decisions Made

- boto3 pinned >=1.39.5 in requirements.txt — Lambda runtime ships an older boto3 without the s3vectors client; SAM must bundle the newer version for `UnknownServiceError: Unknown service: 's3vectors'` not to occur at runtime
- EmbedWorkerFunction is a separate Lambda with 300s timeout — embedding work exceeds the API Gateway 29s hard limit; async invocation from SylliFunction required
- MaterialsTable user_id-index GSI declared at table creation time — DynamoDB does not allow adding GSIs to existing tables without full recreation (data loss risk)
- s3vectors:PutVectors IAM action scoped to EmbedWorkerFunction only — SylliFunction does not need vector write access (least privilege)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Python's yaml.safe_load rejects CloudFormation intrinsic function tags (!Sub, !Ref, !GetAtt) — used custom constructors for YAML validation instead of raw safe_load. YAML structure is valid; SAM will process intrinsic functions correctly at deploy time.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All SAM resources and IAM grants for the materials pipeline are declared
- Plan 03-02 (upload endpoint) can reference MATERIALS_BUCKET, MATERIALS_TABLE, EMBED_FUNCTION_NAME env vars immediately
- Plan 03-03 (embed worker) can implement workers/embed_worker.py with correct IAM (s3vectors:PutVectors, bedrock:InvokeModel)
- Plan 03-04 (library list) can query user_id-index GSI without a full table scan

---
*Phase: 03-materials-and-library*
*Completed: 2026-03-15*
