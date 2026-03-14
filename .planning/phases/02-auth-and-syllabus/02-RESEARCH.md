# Phase 2: Auth and Syllabus - Research

**Researched:** 2026-03-14
**Domain:** Lightweight session-based auth (username + PIN), DynamoDB multi-tenant data scoping, Next.js frontend scaffold, syllabus upload UI, week_map timeline rendering
**Confidence:** HIGH

---

## Summary

Phase 2 has two orthogonal concerns: (1) auth — a lightweight username + PIN session mechanism that gates all user data behind a private namespace, and (2) frontend — the first Next.js UI, which includes login/register, syllabus PDF upload, and timeline rendering.

The critical architectural decision is the DynamoDB partition key. Every future table (materials, conversations, quizzes) will use `user_id` as a partition key prefix or composite key component. Getting this wrong now requires data migration later — there is no retrofitting. The existing `sylli-syllabus-table` has `syllabus_id` as its only partition key with no `user_id` attribute; it must be extended or replaced for multi-user isolation.

Auth is intentionally simple: username + PIN stored in a new `sylli-users-table`, a JWT issued on login, that JWT passed as a Bearer token on all API calls, and the Lambda validating it before touching any user data. No Cognito, no OAuth, no email verification. The constraint is explicit: "Simple auth — username + PIN is sufficient for MVP." The v2 requirement `AUTH-V2-02` defers full Cognito to production.

The frontend is built from scratch (Next.js + TypeScript + Tailwind). This phase delivers only the auth screens (register/login) and the syllabus upload + timeline view. The full three-pane dashboard comes in later phases.

**Primary recommendation:** Add `user_id` (UUID) as a partition key component to all DynamoDB tables from this phase forward. Use JWT (PyJWT on the backend, httpOnly cookie or localStorage on the frontend) for sessions. Build the Next.js app with `create-next-app`, App Router, and Tailwind. Keep auth state in React Context for Phase 2; defer Zustand until Phase 3+ complexity warrants it.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can create a session by entering a username and PIN | New `sylli-users-table` (username PK, hashed_pin, user_id UUID); `POST /api/v1/auth/register` + `POST /api/v1/auth/login`; JWT returned on success |
| AUTH-02 | User's data (syllabus, materials, chat history) is scoped to their username | `user_id` added to `sylli-syllabus-table` items; all dynamo queries filter by `user_id`; JWT middleware extracts `user_id` and passes to services |
| AUTH-03 | User can log out and return with the same username + PIN to access their data | PIN verified against bcrypt hash on login; same JWT flow; logout is client-side token deletion |
| SYLL-01 | User can upload a course syllabus PDF through the UI to initialize their course | Next.js page with `<input type="file" accept=".pdf">` or drag-drop; calls existing `POST /api/v1/syllabus` with auth header |
| SYLL-02 | User can view the parsed week/unit timeline after syllabus upload | Next.js component reads `week_map.weeks[]` and renders a chronological list/accordion; data comes from `GET /api/v1/syllabus/{id}` |
</phase_requirements>

---

## Standard Stack

### Backend — New Libraries
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyJWT | ^2.8 | JWT creation and validation | Lightweight, no Cognito dependency; standard for serverless Python auth |
| bcrypt | ^4.1 | PIN hashing (bcrypt is intentionally slow — good for passwords) | Industry standard; alternatives (argon2) are heavier to install on Lambda |
| passlib[bcrypt] | ^1.7 | bcrypt wrapper with consistent API | Passlib is the FastAPI-recommended hashing library; used in official FastAPI security docs |

### Backend — Already Present (no new installs)
| Library | Version in Use | Purpose |
|---------|---------------|---------|
| FastAPI | in requirements.txt | Auth router, HTTPException(401/403), dependency injection for auth middleware |
| boto3 | Lambda runtime | DynamoDB operations for users table |
| python-multipart | in requirements.txt | Already handles file uploads (no change) |

### Frontend — New Stack
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | ^14 (App Router) | SSR framework; auth redirects in middleware | React ecosystem standard; already specified in PROJECT.md |
| TypeScript | ^5 | Type safety across components | Standard with Next.js |
| Tailwind CSS | ^3 | Utility-first styling | Specified in SPEC.md ("dark-mode first"); fastest path to polished UI |
| React Context | (React built-in) | Auth state (user_id, username, token) | Sufficient for Phase 2; avoids adding Zustand before it's needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT + passlib | boto3 + DynamoDB sessions (server-side sessions) | Server-side sessions require session table; JWT is stateless and fits Lambda better |
| bcrypt via passlib | argon2-cffi | argon2 is stronger but adds native C dependency; harder to package for Lambda ARM64 |
| Next.js App Router | Pages Router | App Router is the current standard; Server Components simplify auth redirects |
| localStorage for JWT | httpOnly Cookie | httpOnly cookie is more secure (no XSS risk); localStorage is simpler to implement; for MVP either works; prefer httpOnly |

### Installation

Backend:
```bash
pip install PyJWT bcrypt passlib[bcrypt]
```

Frontend (from scratch):
```bash
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"
```

---

## Architecture Patterns

### Recommended Project Structure (additions to existing)

Backend additions:
```
backend/
├── routers/
│   ├── auth.py              # POST /api/v1/auth/register, /login
│   └── syllabus.py          # EXISTING — add user_id enforcement
├── services/
│   ├── auth_service.py      # register_user, login_user, hash_pin, verify_pin
│   └── dynamo_service.py    # EXISTING — add store_user, get_user_by_username
└── middleware/
    └── auth.py              # FastAPI dependency: get_current_user(token) -> user_id
```

Frontend (new):
```
frontend/
├── app/
│   ├── layout.tsx           # Root layout, AuthProvider wrapper
│   ├── page.tsx             # Redirect to /login or /dashboard
│   ├── login/
│   │   └── page.tsx         # Login + register form
│   └── dashboard/
│       ├── page.tsx         # Syllabus upload + timeline view
│       └── layout.tsx       # Auth guard (redirect if no token)
├── components/
│   ├── AuthForm.tsx         # Username + PIN form (register/login toggle)
│   ├── SyllabusUpload.tsx   # PDF file input + upload trigger
│   └── WeekTimeline.tsx     # Renders week_map.weeks[] as timeline
├── context/
│   └── AuthContext.tsx      # user_id, username, token state
├── lib/
│   └── api.ts               # Fetch wrapper with auth header injection
└── tailwind.config.ts
```

### Pattern 1: FastAPI Dependency Injection for Auth

**What:** A reusable `get_current_user` dependency that extracts and validates the JWT from the `Authorization: Bearer <token>` header. Inject into any route that requires authentication.

**When to use:** Every route that touches user data (syllabus, materials, chat, quiz).

**Example:**
```python
# Source: FastAPI official security docs — https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Validate JWT and return user_id. Raises 401 on invalid token."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

Usage in any router:
```python
@router.get("/syllabus/{syllabus_id}")
async def get_syllabus(
    syllabus_id: str,
    user_id: str = Depends(get_current_user)
):
    result = await fetch_syllabus(syllabus_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Syllabus not found.")
    return result
```

### Pattern 2: DynamoDB Multi-Tenant Scoping

**What:** Add `user_id` to every DynamoDB item. For the existing `sylli-syllabus-table` (partition key: `syllabus_id`), add `user_id` as a regular attribute and enforce it in all queries. For the new `sylli-users-table`, use `username` as the partition key.

**Critical:** The existing `sylli-syllabus-table` PK is `syllabus_id` — this is fine for Phase 2. The `user_id` will be a non-key attribute used for authorization checks (fetch by `syllabus_id`, then verify `item["user_id"] == requesting_user_id`). Full GSI-based user-scoped listing is a Phase 3 concern.

**New `sylli-users-table` schema:**
```
Partition Key: username (S)
Attributes:
  - user_id: UUID (S)      — used as the stable identity token subject
  - hashed_pin: String (S) — bcrypt hash of the PIN
  - created_at: String (S) — ISO 8601
```

**Store syllabus with user_id:**
```python
# dynamo_service.py addition
def store_syllabus(syllabus_id, filename, s3_key, week_map, uploaded_at, user_id):
    table.put_item(Item={
        "syllabus_id": syllabus_id,
        "user_id": user_id,   # NEW — added for auth scoping
        "filename": filename,
        "s3_key": s3_key,
        "week_map": week_map,
        "uploaded_at": uploaded_at,
    })
```

**Authorization check on retrieval:**
```python
def get_syllabus(syllabus_id: str, user_id: str) -> dict | None:
    result = table.get_item(Key={"syllabus_id": syllabus_id})
    item = result.get("Item")
    if item is None:
        return None
    if item.get("user_id") != user_id:
        return None  # Return None (not found) rather than 403 — avoids enumeration
    return item
```

### Pattern 3: PIN Hashing with passlib

**What:** Hash the PIN before storing; verify on login. Never store plaintext.

**Example:**
```python
# Source: FastAPI docs — https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    return pwd_context.verify(plain_pin, hashed_pin)
```

### Pattern 4: JWT Secret via Lambda Environment Variable

**What:** Store the JWT signing secret in a Lambda environment variable `JWT_SECRET`. For local dev, add to `settings.local.json` or a `.env` file (already gitignored).

**Template.yaml addition:**
```yaml
Environment:
  Variables:
    SYLLABUS_BUCKET: sylli-syllabus-bucket
    SYLLABUS_TABLE: sylli-syllabus-table
    USERS_TABLE: sylli-users-table      # NEW
    JWT_SECRET: !Sub "{{resolve:ssm:/sylli/jwt-secret}}"  # or hardcoded for dev
```

For MVP simplicity, a hardcoded dev secret with an env var override is acceptable:
```python
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_EXPIRY_HOURS = 24 * 7  # 7 days — student sessions are long
```

### Pattern 5: Next.js Auth Guard

**What:** Protect the dashboard route by checking token presence in layout. Redirect to `/login` if absent.

**Example (App Router layout):**
```typescript
// frontend/app/dashboard/layout.tsx
"use client"
import { useAuth } from "@/context/AuthContext"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!token) router.replace("/login")
  }, [token, router])

  if (!token) return null
  return <>{children}</>
}
```

### Pattern 6: Week Map Timeline Rendering

**What:** Render `week_map.weeks[]` as a vertical timeline. Each item shows week number, topic, and readings list.

**Data shape (from existing Bedrock output):**
```json
{
  "course_name": "Introduction to Psychology",
  "weeks": [
    { "week": 1, "topic": "History of Psychology", "readings": ["Chapter 1"], "notes": "..." }
  ]
}
```

**Component sketch:**
```typescript
// frontend/components/WeekTimeline.tsx
interface Week { week: number; topic: string; readings: string[]; notes?: string }
interface WeekMap { course_name: string; weeks: Week[] }

export function WeekTimeline({ weekMap }: { weekMap: WeekMap }) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{weekMap.course_name}</h2>
      {weekMap.weeks.map((w) => (
        <div key={w.week} className="border-l-2 border-blue-500 pl-4">
          <p className="font-medium">Week {w.week}: {w.topic}</p>
          <ul className="text-sm text-gray-400">
            {w.readings.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      ))}
    </div>
  )
}
```

### Anti-Patterns to Avoid

- **Storing plain-text PINs:** Always hash with bcrypt before DynamoDB. Never log or return the PIN.
- **Returning 403 on unauthorized resource access:** Return 404 (not found) for cross-user access attempts — 403 confirms the resource exists, which leaks information.
- **Putting JWT_SECRET in template.yaml source control:** Use an env var or SSM Parameter Store reference for non-local deployments.
- **Querying all items and filtering in Python:** Do not `scan()` the syllabus table looking for a user's data. Always fetch by `syllabus_id` and then check `user_id` on the returned item.
- **Blocking the Lambda on synchronous Next.js SSR for file uploads:** The Next.js frontend uploads directly to the API Gateway/Lambda backend — no need for server-side Next.js file handling.
- **Adding a `user_id` GSI to `sylli-syllabus-table` now:** Phase 2 success criteria only requires upload + timeline view. A GSI for listing all syllabi by user is deferred to Phase 3 (when the library navigator needs it). Don't over-build infrastructure in Phase 2.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PIN hashing | Custom SHA-256 + salt implementation | `passlib[bcrypt]` | bcrypt is intentionally slow (work factor), which is required for security. SHA-256 is too fast and trivially brute-forced. |
| JWT creation and validation | Custom base64 encode + HMAC | `PyJWT` | JWT has edge cases (algorithm confusion attacks, expiry validation off-by-one). PyJWT is audited and handles these. |
| Auth state in Next.js | Redux for user token | React Context + `useContext` | Phase 2 only has auth state (user_id, username, token). Context is sufficient. |
| CORS configuration | Custom middleware | FastAPI built-in `CORSMiddleware` | FastAPI provides `from fastapi.middleware.cors import CORSMiddleware`; one-liner configuration. |
| File upload to Lambda | Custom chunked upload | `multipart/form-data` via existing `python-multipart` | Already working in Phase 1. |

**Key insight:** Auth is a solved problem at this scale. The only custom logic needed is "check username existence" and "compare PIN hash." Everything else (JWT, bcrypt) is library territory.

---

## Common Pitfalls

### Pitfall 1: DynamoDB `user_id` not enforced on retrieval

**What goes wrong:** The syllabus upload stores `user_id` on the item, but the retrieval function only checks `syllabus_id`. User B can access User A's syllabus by guessing the UUID.
**Why it happens:** It's easy to add `user_id` to writes and forget to validate it on reads.
**How to avoid:** After every `get_item(Key={"syllabus_id": ...})`, check `item["user_id"] == requesting_user_id`. Return `None` (404) on mismatch, not 403.
**Warning signs:** UAT step: "log in as user B, request syllabus_id from user A" should return 404; if it returns data, enforcement is missing.

### Pitfall 2: bcrypt import fails on Lambda ARM64

**What goes wrong:** `import bcrypt` succeeds locally (x86) but fails on Lambda ARM64 because bcrypt has a C extension that must be compiled for the target architecture.
**Why it happens:** `pip install bcrypt` on a Mac M1/M2 compiles for arm64 Darwin, not Amazon Linux ARM64. The binary is incompatible.
**How to avoid:** Build with `sam build --use-container` which builds inside a Docker container matching the Lambda runtime. Alternatively, use `sam build` with the `--use-container` flag always.
**Warning signs:** `Runtime.ImportModuleError: No module named 'bcrypt._bcrypt'` in Lambda logs.

### Pitfall 3: JWT algorithm confusion attack

**What goes wrong:** Decoder accepts `alg: none` JWT or RS256-signed tokens when configured for HS256.
**Why it happens:** PyJWT < 2.0 had this vulnerability. PyJWT >= 2.0 requires explicit `algorithms=["HS256"]` parameter in `jwt.decode()`.
**How to avoid:** Always pass `algorithms=["HS256"]` (a list, not a string) to `jwt.decode()`. PyJWT 2.x enforces this.
**Warning signs:** PyJWT >= 2.x will raise `DecodeError` if `algorithms` is not passed.

### Pitfall 4: `sylli-users-table` username uniqueness — DynamoDB has no UNIQUE constraint

**What goes wrong:** Two users register with the same username; second write overwrites the first because DynamoDB `put_item` is an upsert by default.
**Why it happens:** DynamoDB has no UNIQUE constraint — it's a key-value store.
**How to avoid:** Use a conditional write: `table.put_item(Item={...}, ConditionExpression="attribute_not_exists(username)")`. This raises `ConditionalCheckFailedException` if username already exists.
**Warning signs:** User registration silently overwrites another user's data.

### Pitfall 5: `week_map` attribute naming — Bedrock output is not guaranteed to match schema

**What goes wrong:** Frontend `WeekTimeline` component assumes `week_map.weeks[]` but Bedrock occasionally returns `week_map.week_list` or omits `notes`. The component crashes with `Cannot read properties of undefined`.
**Why it happens:** Bedrock is a language model; its JSON output structure can vary despite the system prompt.
**How to avoid:** Add defensive defaults in the component: `weekMap?.weeks ?? []` and `w.notes ?? ""`. The backend Bedrock service already handles parse failures (Phase 1 work), so a well-formed but structurally variant week_map should be treated gracefully by the frontend.
**Warning signs:** White screen on dashboard after upload; browser console shows `TypeError`.

### Pitfall 6: Next.js CORS — API Gateway not configured for localhost:3000

**What goes wrong:** Next.js dev server on `localhost:3000` gets CORS errors when calling the API Gateway endpoint.
**Why it happens:** API Gateway / Lambda does not return CORS headers unless configured.
**How to avoid:** Add `CORSMiddleware` to FastAPI:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.amplifyapp.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Warning signs:** Browser console: `Access to fetch at '...' has been blocked by CORS policy`.

### Pitfall 7: PIN validation — no length/format constraints opens brute force

**What goes wrong:** A 1-digit PIN "1" is stored and accepted. The bcrypt cost factor alone is not enough defense at this app's volume, but it's also inconsistent UX.
**Why it happens:** No server-side input validation added.
**How to avoid:** Validate PIN is 4–8 digits on both frontend (HTML pattern) and backend (FastAPI validators). Username minimum 3 characters.

---

## Code Examples

### Register endpoint

```python
# Source: FastAPI + PyJWT + passlib pattern — verified against official FastAPI docs
# backend/routers/auth.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.auth_service import register_user, login_user

router = APIRouter()

class AuthRequest(BaseModel):
    username: str
    pin: str

@router.post("/auth/register", tags=["auth"])
async def register(body: AuthRequest):
    try:
        token = await register_user(body.username, body.pin)
        return {"token": token}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))  # username taken

@router.post("/auth/login", tags=["auth"])
async def login(body: AuthRequest):
    token = await login_user(body.username, body.pin)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid username or PIN")
    return {"token": token}
```

### Auth service

```python
# backend/services/auth_service.py
import os
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
from services.dynamo_service import store_user, get_user_by_username

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7

async def register_user(username: str, pin: str) -> str:
    existing = get_user_by_username(username)
    if existing:
        raise ValueError("Username already taken")
    user_id = str(uuid.uuid4())
    hashed_pin = pwd_context.hash(pin)
    store_user(username=username, user_id=user_id, hashed_pin=hashed_pin)
    return _create_token(user_id, username)

async def login_user(username: str, pin: str) -> str | None:
    user = get_user_by_username(username)
    if not user or not pwd_context.verify(pin, user["hashed_pin"]):
        return None
    return _create_token(user["user_id"], username)

def _create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
```

### DynamoDB users table operations

```python
# Addition to backend/services/dynamo_service.py
USERS_TABLE_NAME = os.getenv("USERS_TABLE", "sylli-users-table")

def store_user(username: str, user_id: str, hashed_pin: str):
    """Store a new user. Raises ClientError if username already exists."""
    table = dynamodb.Table(USERS_TABLE_NAME)
    from botocore.exceptions import ClientError
    try:
        table.put_item(
            Item={
                "username": username,
                "user_id": user_id,
                "hashed_pin": hashed_pin,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            ConditionExpression="attribute_not_exists(username)"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError("Username already taken")
        raise

def get_user_by_username(username: str) -> dict | None:
    table = dynamodb.Table(USERS_TABLE_NAME)
    result = table.get_item(Key={"username": username})
    return result.get("Item")
```

### CloudFormation addition for users table

```yaml
# Addition to template.yaml Resources:
UsersTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: sylli-users-table
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: username
        AttributeType: S
    KeySchema:
      - AttributeName: username
        KeyType: HASH

# Addition to SylliFunction Policies:
- DynamoDBWritePolicy:
    TableName: sylli-users-table
- DynamoDBReadPolicy:
    TableName: sylli-users-table

# Addition to SylliFunction Environment Variables:
USERS_TABLE: sylli-users-table
JWT_SECRET: "dev-secret-replace-for-prod"
```

### Next.js AuthContext

```typescript
// frontend/context/AuthContext.tsx
"use client"
import { createContext, useContext, useState, ReactNode } from "react"

interface AuthState {
  token: string | null
  user_id: string | null
  username: string | null
}

interface AuthContextType extends AuthState {
  setAuth: (token: string, user_id: string, username: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuthState] = useState<AuthState>({
    token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
    user_id: typeof window !== "undefined" ? localStorage.getItem("user_id") : null,
    username: typeof window !== "undefined" ? localStorage.getItem("username") : null,
  })

  const setAuth = (token: string, user_id: string, username: string) => {
    localStorage.setItem("token", token)
    localStorage.setItem("user_id", user_id)
    localStorage.setItem("username", username)
    setAuthState({ token, user_id, username })
  }

  const logout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("user_id")
    localStorage.removeItem("username")
    setAuthState({ token: null, user_id: null, username: null })
  }

  return <AuthContext.Provider value={{ ...auth, setAuth, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js Pages Router (`pages/`) | App Router (`app/`) | Next.js 13 (stable in 14) | Layouts, Server Components, middleware-based auth redirects |
| `getServerSideProps` for auth | Server Components + `cookies()` or client-side `useEffect` redirect | Next.js 13+ | Simpler auth guard patterns |
| `jose` for JWT in Next.js | `jose` still standard for Edge; `PyJWT` for Python | — | PyJWT is Python-only; Next.js middleware uses `jose` if needed |
| Cognito for all auth | Simple JWT for MVP | Project decision | Cognito is AUTH-V2-02 (out of scope for MVP) |

**Not deprecated in this project:**
- `passlib[bcrypt]`: Still the FastAPI-recommended hashing approach as of 2026
- `PyJWT >= 2.0`: Current, secure, `algorithms` parameter required

---

## Open Questions

1. **JWT_SECRET management for deployed Lambda**
   - What we know: A hardcoded dev secret is fine locally. For `sam deploy`, the secret needs to exist somehow.
   - What's unclear: Whether the project uses AWS SSM Parameter Store or just accepts a hardcoded dev secret (given the MVP/no-production scope).
   - Recommendation: For Phase 2, use a hardcoded env var in `template.yaml` with a clear `# TODO: use SSM for prod` comment. The requirements explicitly state this won't go to production.

2. **Where to store the JWT on the frontend**
   - What we know: `localStorage` is simpler; `httpOnly` cookies are more secure (XSS-safe).
   - What's unclear: No explicit user decision captured.
   - Recommendation: Use `localStorage` for Phase 2 (simpler, no backend cookie handling needed). The app won't go to production per requirements, so XSS risk is acceptable at MVP.

3. **Existing `sylli-syllabus-table` items (backward compatibility)**
   - What we know: Phase 1 tests may have written items to the table without `user_id`.
   - What's unclear: Whether any existing data needs to be preserved.
   - Recommendation: Phase 2 code should treat items without `user_id` as orphaned and return 404. No migration needed — this is a dev environment.

4. **Frontend hosting for development**
   - What we know: SPEC.md lists AWS Amplify as hosting. Phase 2 is development-only.
   - What's unclear: Whether Phase 2 includes Amplify deployment or just local Next.js dev server.
   - Recommendation: Phase 2 success criteria (`A logged-in user can upload a course syllabus PDF through the Next.js UI`) can be satisfied with `next dev` locally. Amplify deployment is Phase 5 work per SPEC.md.

---

## Sources

### Primary (HIGH confidence)
- Direct read of `/Users/tanmaygoel/CS/Sylli/backend/services/dynamo_service.py` — confirmed existing table schema and operations
- Direct read of `/Users/tanmaygoel/CS/Sylli/backend/services/syllabus_service.py` — confirmed upload flow, no `user_id` present
- Direct read of `/Users/tanmaygoel/CS/Sylli/template.yaml` — confirmed DynamoDB table definition (partition key `syllabus_id`), existing policies
- Direct read of `/Users/tanmaygoel/CS/Sylli/SPEC.md` — confirmed frontend stack (Next.js, Tailwind), auth scope, data models
- Direct read of `/Users/tanmaygoel/CS/Sylli/.planning/REQUIREMENTS.md` — AUTH-01/02/03, SYLL-01/02 requirements
- FastAPI Security docs: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- PyJWT documentation: https://pyjwt.readthedocs.io/en/stable/
- DynamoDB conditional writes: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.OperatorsAndFunctions.html
- Next.js App Router docs: https://nextjs.org/docs/app

### Secondary (MEDIUM confidence)
- bcrypt ARM64 Lambda packaging: known limitation from community reports; mitigation (`sam build --use-container`) is well-documented
- passlib[bcrypt] as FastAPI-recommended approach: referenced in FastAPI official tutorial

### Tertiary (LOW confidence)
- None — all critical claims are either direct code inspection or FastAPI/AWS/Next.js official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — PyJWT + passlib are specified in FastAPI official docs; Next.js + Tailwind are specified in SPEC.md
- Architecture: HIGH — patterns derived directly from existing codebase conventions (service layer, router/service split, DynamoDB operations)
- Pitfalls: HIGH — bcrypt ARM64 is well-documented; JWT algorithm confusion is PyJWT 2.x documented behavior; DynamoDB uniqueness constraint is a fundamental DynamoDB property
- DynamoDB data model: HIGH — partition key analysis based on direct table schema inspection

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (PyJWT, passlib, Next.js App Router APIs are stable; DynamoDB conditional writes are invariant)
