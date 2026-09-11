# APIFlow — System Design Document

Companion to `PRD.md`. This document covers *how* the system is built: architecture, data model, API contracts, security flows, AI agent design, and deployment. `Phase1_Part1_PRD.md` and `Tasks.md` scope *what* gets built in what order.

---

## 1. System Overview

APIFlow is a three-tier web application:

- **Client tier:** React SPA (Vite) — request builder UI, workspace/collection management, auth screens
- **Application tier:** FastAPI backend — REST API + (Phase 2) WebSocket server, layered as routes → services → repositories
- **Data tier:** PostgreSQL (source of truth), Redis (Phase 2 — cache, rate limiting, token blocklist)

The backend also acts as an **outbound HTTP proxy** for the "Send Request" feature — it is not just a CRUD API, it makes real network calls on the user's behalf and records the results. In Phase 2, it also hosts two narrow, single-purpose **AI agents** (Module 13) that read from the same database — no external tool-calling protocol involved.

---

## 2. High-Level Architecture

### Phase 1 topology (managed platform)
```
┌──────────────────────────────────────────────────────────┐
│                        Browser                            │
│  React SPA (Vite + Tailwind + React Router) — on Vercel   │
└───────────────────────┬────────────────────────────────────┘
                         │  HTTPS (REST/JSON)
                         ▼
              FastAPI Backend (Render/Railway, managed)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       PostgreSQL (Neon/Supabase)  Target APIs (proxied outbound calls)
```
Phase 1 deliberately uses a managed platform for the backend so review-panel deadlines aren't spent on server administration (PRD §10, decision 5). HTTPS, process management, and restarts are handled by the platform.

### Phase 2 topology (self-managed Linux VM + Nginx)
```
┌──────────────────────────────────────────────────────────┐
│                        Browser                            │
│  React SPA (Vite + Tailwind + React Router) — on Vercel   │
└───────────────────────┬────────────────────────────────────┘
                         │  HTTPS (REST/JSON) + WSS
                         ▼
┌──────────────────────────────────────────────────────────┐
│         Linux VM — Oracle Cloud Free Tier (ARM)            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Nginx (reverse proxy, SSL termination via Certbot) │  │
│  └───────────────────────┬────────────────────────────┘  │
│                           ▼                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (Docker container)                 │  │
│  │  api/ → services/ → repositories/                   │  │
│  │  - Auth middleware (JWT, RBAC)                       │  │
│  │  - websockets/ (Phase 2)                              │  │
│  │  - services/ai/ (Documentation Agent, Testing Agent) │  │
│  └────────────┬───────────────────────┬─────────────────┘  │
│               ▼                       ▼                    │
│      ┌────────────────┐      ┌───────────────┐            │
│      │ PostgreSQL      │      │ Redis          │            │
│      │ (Docker, same VM│      │ (Docker,       │            │
│      │  or managed)    │      │  same VM)      │            │
│      └────────────────┘      └───────────────┘            │
│  Firewall: only 22 (SSH, key-only), 80, 443 open           │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
                  Target APIs (proxied outbound calls)
                         │
                         ▼
                  Groq API (LLM calls, Documentation/Testing agents)
```

**Request flow example (Send Request):**
`Browser → Nginx → FastAPI /requests/{id}/send → services/request_service → outbound HTTP call to target API → response saved to response_history → response returned to Browser`

---

## 3. Backend Layering (Clean Architecture-lite)

```
app/
  api/              # thin route handlers — parse input, call service, return response
    auth.py
    workspaces.py
    collections.py
    requests.py
    environments.py
    search.py
    comments.py         # Phase 2
    versions.py          # Phase 2
    ai.py                 # Phase 2 — Documentation Agent + Testing Agent endpoints
    websockets.py         # Phase 2

  services/          # business logic — the only layer that makes decisions
    auth_service.py
    workspace_service.py
    collection_service.py
    request_service.py       # includes proxy/send logic
    freshness_service.py     # Module 16 — drift scoring
    environment_service.py
    ai/
      documentation_agent.py   # Phase 2
      testing_agent.py          # Phase 2
      llm_client.py              # Phase 2 — thin wrapper around Groq API

  repositories/       # DB access only — no business logic
    user_repository.py
    workspace_repository.py
    collection_repository.py
    request_repository.py
    response_history_repository.py

  models/             # SQLAlchemy ORM models (1:1 with DB tables)
  schemas/            # Pydantic — request/response contracts, separate from ORM models
  core/
    config.py         # env var loading (pydantic-settings)
    security.py        # password hashing, JWT encode/decode
    deps.py            # FastAPI dependencies: get_current_user, require_role()
    rate_limit.py       # Phase 2

  main.py             # app factory, router registration, middleware
```

**Rule:** routes never talk to repositories directly, and repositories never contain business rules (e.g. "can this user edit this request?" lives in `services/`, not `api/` or `repositories/`). The AI agents follow the same pattern: `api/ai.py` is thin, `services/ai/*` contains the actual prompting/comparison logic, and both agents read through the existing repositories — **no new data-access pattern, no external tool-calling protocol** (see §9 for why MCP is explicitly out of scope).

---

## 4. Data Model

### 4.1 Entity Relationship Overview

```
users ──< workspace_members >── workspaces ──< collections ──< requests ──< response_history
  │                                   │                              │
  ├──< oauth_accounts                 ├──< environments ──< environment_variables
  └──< refresh_tokens                 │
                                       └──< (Phase 2) comments, request_versions
```

### 4.2 Table Definitions

**users**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| email | varchar, unique, indexed | |
| password_hash | varchar, nullable | null if OAuth-only account |
| name | varchar | |
| avatar_url | varchar, nullable | |
| is_verified | boolean, default false | |
| created_at | timestamptz | |

**oauth_accounts**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users, indexed) | |
| provider | varchar | e.g. `"google"` |
| provider_user_id | varchar | provider's unique subject ID |
| — unique constraint on (`provider`, `provider_user_id`) | | prevents duplicate linking |

**refresh_tokens**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users, indexed) | |
| token_hash | varchar | never store raw token |
| expires_at | timestamptz | |
| revoked | boolean, default false | |
| created_at | timestamptz | |

**workspaces**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| name | varchar | |
| owner_id | UUID (FK → users) | |
| created_at | timestamptz | |

**workspace_members**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| workspace_id | UUID (FK → workspaces, indexed) | |
| user_id | UUID (FK → users, indexed) | |
| role | enum: owner / admin / member / viewer | |
| joined_at | timestamptz | |
| — unique constraint on (`workspace_id`, `user_id`) | | one membership row per user per workspace |

**collections**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| workspace_id | UUID (FK → workspaces, indexed) | |
| name | varchar | |
| created_by | UUID (FK → users) | |
| created_at | timestamptz | |

**requests**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| collection_id | UUID (FK → collections, indexed) | |
| name | varchar | |
| method | enum: GET/POST/PUT/PATCH/DELETE | |
| url | text | may contain `{{VAR}}` placeholders |
| headers | JSONB | |
| params | JSONB | |
| body | JSONB, nullable | |
| description | text, nullable | Markdown |
| created_by | UUID (FK → users) | |
| updated_by | UUID (FK → users) | |
| created_at | timestamptz | |
| updated_at | timestamptz | bumped on any definition change |
| description_updated_at | timestamptz, nullable | bumped only when `description` changes — needed to compute drift independent of `updated_at` |
| last_verified_at | timestamptz, nullable | set on last **successful** (2xx) send |
| expected_response_shape | JSONB, nullable | Phase 2 — top-level field names/types of the last-known-good response, maintained by the Testing Agent; used to detect shape drift, not just status-code drift |

**environments**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| workspace_id | UUID (FK → workspaces, indexed) | |
| name | varchar | e.g. "Development" |

**environment_variables**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| environment_id | UUID (FK → environments, indexed) | |
| key | varchar | |
| value | text | |
| is_secret | boolean, default false | masked in UI if true |

**response_history**
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| request_id | UUID (FK → requests, indexed) | |
| status_code | int | |
| response_body | JSONB | truncated/size-capped, see §7 |
| response_headers | JSONB | |
| time_taken_ms | int | |
| sent_at | timestamptz, indexed | |
| sent_by | UUID (FK → users, nullable) | null if triggered by the Testing Agent rather than a human |
| triggered_by | enum: `user` / `testing_agent`, default `user` | distinguishes manual sends from agent-run regression checks |

**comments** *(Phase 2)*
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| request_id | UUID (FK → requests, indexed) | |
| user_id | UUID (FK → users) | |
| body | text | |
| resolved | boolean, default false | |
| parent_comment_id | UUID, nullable, self-FK | for threaded replies |
| created_at | timestamptz | |

**request_versions** *(Phase 2)*
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| request_id | UUID (FK → requests, indexed) | |
| snapshot | JSONB | full request state at time of change |
| changed_by | UUID (FK → users) | |
| changed_at | timestamptz | |

**test_runs** *(Phase 2 — Testing Agent)*
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| collection_id | UUID (FK → collections, indexed) | |
| triggered_by | UUID (FK → users) | who ran it |
| started_at | timestamptz | |
| completed_at | timestamptz, nullable | |
| status | enum: running / completed / failed | |
| summary | text, nullable | plain-English overall summary, generated after all requests in the run complete |

**test_run_results** *(Phase 2 — Testing Agent)*
| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| test_run_id | UUID (FK → test_runs, indexed) | |
| request_id | UUID (FK → requests) | |
| response_history_id | UUID (FK → response_history) | the actual send this result is based on |
| passed | boolean | |
| explanation | text, nullable | plain-English diff explanation, only populated on failure |

### 4.3 Multi-Tenancy Enforcement

- Every table below `workspaces` traces back to a `workspace_id`, directly or via its parent (`collections.workspace_id`, `requests → collections.workspace_id`, `test_runs → collections.workspace_id`, etc.)
- **Enforcement point:** the **service layer**, not just route-level decorators. Every service method that touches a workspace-scoped resource takes `current_user` and first resolves/validates `workspace_membership` before doing anything else.
- Repository layer never trusts a bare `id` alone for workspace-scoped fetches without a workspace-membership check having already occurred upstream, to avoid IDOR — the risk isn't "can you know a request exists" but "can you read/edit a request in a workspace you're not in."
- The AI agents inherit this automatically: both operate through `request_service`/`collection_service`, which already enforce membership — an agent can never read across workspace boundaries.

---

## 5. API Design

Base path: `/api/v1`. All responses JSON. Auth via `Authorization: Bearer <access_token>` unless noted.

### 5.1 Auth
| Method | Path | Auth | Body / Notes |
|---|---|---|---|
| POST | `/auth/signup` | none | `{email, password, name}` → `{user}` |
| POST | `/auth/login` | none | `{email, password}` → `{access_token, refresh_token, user}` |
| POST | `/auth/refresh` | refresh token (body or httpOnly cookie) | → new `{access_token, refresh_token}`; old refresh token revoked |
| POST | `/auth/logout` | access token | revokes current refresh token |
| GET | `/auth/google/login` | none | redirects to Google consent screen |
| GET | `/auth/google/callback` | none | Google redirect target; issues tokens |
| POST | `/auth/forgot-password` | none | `{email}` → sends reset email, always 200 (no user enumeration) |
| POST | `/auth/reset-password` | reset token | `{token, new_password}` |
| GET | `/auth/me` | access token | → current user |

### 5.2 Workspaces
| Method | Path | Notes |
|---|---|---|
| POST | `/workspaces` | create; creator becomes Owner |
| GET | `/workspaces` | list workspaces current user belongs to |
| GET | `/workspaces/{id}` | requires membership |
| PATCH | `/workspaces/{id}` | rename; requires Admin+ |
| DELETE | `/workspaces/{id}` | requires Owner |
| POST | `/workspaces/{id}/invites` | requires Admin+; `{email, role}` → invite link/token |
| POST | `/workspaces/invites/{token}/accept` | joins the inviting workspace |
| PATCH | `/workspaces/{id}/members/{user_id}` | change role; requires Admin+ |

### 5.3 Collections
| Method | Path | Notes |
|---|---|---|
| POST | `/workspaces/{ws_id}/collections` | requires Member+ |
| GET | `/workspaces/{ws_id}/collections` | requires Viewer+ |
| PATCH | `/collections/{id}` | rename; requires Member+ |
| DELETE | `/collections/{id}` | requires Admin+ |

### 5.4 Requests
| Method | Path | Notes |
|---|---|---|
| POST | `/collections/{id}/requests` | create saved request |
| GET | `/collections/{id}/requests` | list |
| GET | `/requests/{id}` | includes computed `freshness` block, see §5.7 |
| PATCH | `/requests/{id}` | update definition; bumps `updated_at`; if `description` changed, also bumps `description_updated_at` |
| DELETE | `/requests/{id}` | |
| POST | `/requests/{id}/duplicate` | |
| POST | `/requests/{id}/send` | proxies outbound call, writes `response_history`, updates `last_verified_at` on 2xx |
| GET | `/requests/{id}/history` | paginated response_history for this request |

### 5.5 Environments
| Method | Path | Notes |
|---|---|---|
| POST | `/workspaces/{ws_id}/environments` | |
| GET | `/workspaces/{ws_id}/environments` | |
| PATCH | `/environments/{id}` | |
| POST | `/environments/{id}/variables` | `{key, value, is_secret}` |
| PATCH | `/environments/{id}/variables/{var_id}` | |
| DELETE | `/environments/{id}/variables/{var_id}` | |

### 5.6 Search
| Method | Path | Notes |
|---|---|---|
| GET | `/workspaces/{ws_id}/search?q=` | text match on collection/request names (Phase 1: `ILIKE`; Phase 2: Postgres full-text) |

### 5.7 Freshness / Drift (Module 16 — computed, no dedicated write endpoints in MVP)
`GET /requests/{id}` response includes:
```json
{
  "id": "...",
  "method": "POST",
  "url": "...",
  "...": "...",
  "freshness": {
    "status": "stale" | "fresh" | "unverified",
    "definition_updated_at": "2026-07-10T12:00:00Z",
    "description_updated_at": "2026-06-01T09:00:00Z",
    "last_verified_at": "2026-07-15T08:00:00Z",
    "ready_for_handoff": true
  }
}
```
Rule (Phase 1, basic): `status = "stale"` if `definition_updated_at > description_updated_at`. Phase 2 (Module 16) extends this to also weigh `last_verified_at` recency and produce the `ready_for_handoff` badge — see §10.

### 5.8 Phase 2 additions

**Comments, versions, import/export, notifications, WebSocket** — unchanged from prior design:
- `POST/GET /requests/{id}/comments`, `PATCH /comments/{id}/resolve`
- `GET /requests/{id}/versions`, `GET /requests/{id}/versions/diff?from=&to=`, `POST /requests/{id}/versions/{version_id}/restore`
- `POST /workspaces/{ws_id}/import` (OpenAPI JSON), `GET /workspaces/{ws_id}/export`
- `WS /ws/workspaces/{ws_id}` — events: `presence.join`, `presence.leave`, `request.updated`, `comment.created`

**AI Agents (Module 13):**
| Method | Path | Notes |
|---|---|---|
| POST | `/requests/{id}/ai/generate-description` | Documentation Agent — one LLM call using the request definition + most recent `response_history` as context; returns a draft description the user can edit before saving (does not auto-save) |
| GET | `/requests/{id}/ai/shape-check` | Documentation Agent — compares the most recent response against `expected_response_shape`; returns whether the shape still matches and, if not, a plain-English note of what's different |
| POST | `/collections/{id}/ai/test-run` | Testing Agent — kicks off a `test_runs` row, re-sends every request in the collection sequentially (reusing the existing `/requests/{id}/send` proxy logic), compares each against its own `expected_response_shape`/last-known-good response, returns `test_run_id` immediately (async; poll for completion) |
| GET | `/test-runs/{id}` | poll status; when `completed`, includes `summary` and the list of `test_run_results` with `passed`/`explanation` per request |

---

## 6. Authentication & Authorization Design

### 6.1 Token flow
```
Login/Signup
   │
   ▼
Issue: access_token (JWT, 15 min, contains sub=user_id, exp)
        refresh_token (opaque random string, stored server-side as bcrypt/sha256 hash)
   │
   ▼
Client stores access_token in memory (React context, NOT localStorage)
Client stores refresh_token in httpOnly, Secure, SameSite=Strict cookie
   │
   ▼
On 401 (access token expired):
  Client calls POST /auth/refresh (cookie sent automatically)
  Server: looks up token_hash, checks not expired/revoked,
          issues NEW access+refresh pair, REVOKES old refresh token (rotation),
          if a revoked/unknown refresh token is reused → treat as theft,
          revoke ALL refresh tokens for that user (defense-in-depth)
```

### 6.2 RBAC
- Roles are per-workspace, not global: `Owner > Admin > Member > Viewer`
- Enforced via a FastAPI dependency: `require_role(workspace_id, minimum="member")` used on route handlers, but the *actual* check (membership lookup + role comparison) lives in `services/`, callable independently so it's testable without spinning up HTTP
- Permission matrix (summary):

| Action | Viewer | Member | Admin | Owner |
|---|---|---|---|---|
| View requests/collections | ✅ | ✅ | ✅ | ✅ |
| Create/edit requests | ❌ | ✅ | ✅ | ✅ |
| Create/delete collections | ❌ | ✅ | ✅ | ✅ |
| Run Testing Agent on a collection | ❌ | ✅ | ✅ | ✅ |
| Invite members | ❌ | ❌ | ✅ | ✅ |
| Change member roles | ❌ | ❌ | ✅ | ✅ |
| Delete workspace | ❌ | ❌ | ❌ | ✅ |

### 6.3 Google OAuth2
- Standard Authorization Code flow via `authlib`
- Callback: look up `oauth_accounts` by `(provider, provider_user_id)`; if found, log in; if not found but email matches an existing password account, link accounts; if neither, create a new user with `password_hash = null`

---

## 7. "Send Request" Proxy — Detailed Sequence

```
Browser                FastAPI                  Target API
   │  POST /requests/{id}/send                       │
   │  {environment_id?}                                │
   ├──────────────────────►│                            │
   │                        │ 1. load request, check membership
   │                        │ 2. resolve {{VARS}} using environment
   │                        │ 3. build outbound httpx request
   │                        │ 4. enforce timeout (e.g. 15s) and
   │                        │    Phase 2: Redis rate limit check
   │                        ├───────────────────────────►│
   │                        │                            │ (real network call)
   │                        │◄───────────────────────────┤
   │                        │ 5. capture status, headers, body, timing
   │                        │ 6. write response_history row (triggered_by=user)
   │                        │ 7. if 2xx: update requests.last_verified_at
   │◄──────────────────────┤                            │
   │  {status, headers,     │                            │
   │   body, time_taken_ms} │                            │
```

**Why proxy, not direct browser call:** avoids CORS failures against arbitrary target APIs, keeps the user's real IP/network out of the target's logs, and — critically for this product's thesis — makes every "send" a server-recorded, timestamped execution event that `last_verified_at`, the freshness score, and the Testing Agent all depend on. A client-side send would be unverifiable.

**Safety notes:** outbound requests should have a strict timeout, a response body size cap (e.g. 1MB) before truncation, and should not be allowed to target internal/private IP ranges (basic SSRF guard) — validate the resolved host isn't loopback/link-local/private before dispatching. The Testing Agent's collection-wide re-runs reuse this exact same proxy path (`triggered_by=testing_agent`) so there is only one code path that ever makes outbound calls.

---

## 8. Realtime Design (Phase 2)

- One WebSocket connection per open workspace tab: `WS /ws/workspaces/{ws_id}` — connection upgrade validates the same JWT + membership check as REST
- Server maintains an in-memory (Phase 1 of Phase 2: per-instance; later: Redis pub/sub if scaled to multiple backend instances) map of `workspace_id → set of connected user sessions`
- Events broadcast to all sockets in a workspace room:
  - `presence.join` / `presence.leave` — who's currently viewing
  - `request.updated` — payload includes the changed request's id + updater, client re-fetches or merges
  - `comment.created` — new comment notification
  - `test_run.completed` — lets the UI update a running Testing Agent status without polling once WebSockets are live (polling via `GET /test-runs/{id}` remains the fallback)
- Client reconciles by re-fetching the affected resource rather than trusting the WS payload as the full state (avoids partial-update bugs)

---

## 9. AI Agent Design (Module 13)

Two narrow, single-purpose agents. Neither is a general-purpose autonomous agent, and neither uses MCP or any external tool-calling protocol — both only need read access to APIFlow's own database, which is a normal internal query through the existing service/repository layers, not a case for a standardized *external* tool protocol (per PRD §10, decision 4). This keeps the AI surface small, explainable, and cheap to demo in a viva.

### 9.1 Documentation Agent
- **Trigger:** manual button in the Request Builder ("Generate description"), or on-demand shape check
- **`generate-description`:** single LLM call. Prompt context = request method/url/headers/params/body + the most recent `response_history` entry (status, body). Output: a draft Markdown description. The agent never writes directly to `requests.description` — it returns a draft, the user reviews/edits and saves explicitly (keeps a human in the loop, and keeps `description_updated_at` semantics meaningful).
- **`shape-check`:** compares the top-level keys/types of the latest response against `requests.expected_response_shape`. If they differ, returns a plain-English note (e.g. "the response no longer includes a `user.avatar_url` field"). This is a **separate, opt-in** signal from Module 16's freshness score — freshness stays purely timestamp-based and deterministic (PRD §10, decision 6); shape-check is an LLM-assisted addition a user can consult, not something the core freshness badge depends on.

### 9.2 Testing Agent
- **Trigger:** manual "Run tests" action on a collection
- **Flow:**
  1. Create a `test_runs` row (`status=running`)
  2. Sequentially call the existing `request_service.send_request()` for every request in the collection (reusing the proxy path, §7) — no new outbound-call logic
  3. For each request: compare the new response against the best available baseline — `expected_response_shape` if set, otherwise the previous `response_history` entry for that request
  4. On mismatch, one LLM call generates a short plain-English explanation (e.g. "status code changed from 200 to 401 — this endpoint may now require authentication") — write to `test_run_results.explanation`
  5. On completion, one final LLM call summarizes the whole run (`test_runs.summary`), e.g. "3 of 12 endpoints failed, all related to the Orders collection after today's auth change"
  6. Update `test_runs.status = completed`, broadcast `test_run.completed` over WebSocket if connected (§8)
- **Scope boundary:** the agent only *reports*; it never edits a request definition, never retries with different parameters, and never takes corrective action. This is what keeps it "a smart regression-test runner with natural-language reporting," not an autonomous agent — a deliberate scope line from PRD §10, decision 3.

### 9.3 LLM client
- `services/ai/llm_client.py` — thin wrapper around the Groq API (or equivalent free-tier provider), single responsibility: build a prompt, call the API, return text. Both agents depend on this, not on each other or on any framework.
- Failure handling: if the LLM call fails or times out, the agent returns a clear "AI assistance unavailable, try again" response — it never blocks or degrades the underlying feature (saving a request, sending a request, viewing freshness) it's attached to.

---

## 10. Documentation Freshness / Drift Detection Design (Module 16)

This is the product's core differentiator, so its logic is isolated in `services/freshness_service.py`, independently unit-testable, and **does not depend on the AI agents or an LLM being available** (PRD §10, decision 6).

**Inputs per request:** `updated_at` (definition), `description_updated_at`, `last_verified_at`, most recent `response_history.status_code`.

**Phase 1 rule (binary):**
```
stale = updated_at > description_updated_at
```

**Phase 2 rule (scored):**
```
freshness_score = weighted combination of:
  - recency of last_verified_at (has it been executed recently, and did it succeed?)
  - whether description_updated_at postdates the most recent definition change
  - whether the most recent response_history entry was a failure (4xx/5xx) since last_verified_at

ready_for_handoff = (
  description_updated_at >= updated_at
  AND last_verified_at is not null
  AND last_verified_at >= updated_at
  AND most recent response was 2xx
)
```
- This stays **rule-based and deterministic**, so it's demoable without depending on an external AI provider being up.
- The Documentation Agent's `shape-check` (§9.1) is an optional, separate signal a user can consult — it never feeds into `freshness_score` or `ready_for_handoff`.

---

## 11. Caching & Rate Limiting (Redis, Phase 2)

| Use case | Key pattern | TTL |
|---|---|---|
| Workspace/collection read cache | `ws:{id}:collections` | short (~30s), invalidated on write |
| Send-request rate limit | `ratelimit:user:{id}:send` (sliding window / token bucket) | per-minute window |
| Testing Agent run rate limit | `ratelimit:user:{id}:test-run` — separate, stricter bucket since one run fans out into many sends + LLM calls | per-hour window |
| Refresh token blocklist | `blocklist:refresh:{token_hash}` | until token's natural expiry |

Cache invalidation is explicit (delete-on-write), not TTL-only, for anything a user could immediately expect to see updated (e.g. after creating a collection).

---

## 12. Error Handling & Logging

- All API errors return a consistent shape: `{"error": {"code": "...", "message": "..."}}`
- Validation errors surface Pydantic's field-level detail
- Structured logging (JSON lines) for: auth events (login, failed login, token refresh/reuse-detected), workspace/role changes, outbound proxy calls (target host, status, duration — never log request/response bodies that may contain secrets), AI agent calls (which agent, request/collection id, success/failure — never log the LLM prompt/response body verbatim if it may contain secrets from headers/env vars), and unhandled exceptions
- `is_secret` environment variables are never logged or included in outbound-call logs or LLM prompts

---

## 13. Deployment Architecture

### 13.1 Phase 1 — managed platform
```
GitHub repo
   │  push/merge to main
   ▼
GitHub Actions (CI/CD)
   │  lint + pytest
   ├──► Frontend build ──► deploy ──► Vercel
   └──► Backend image ──► deploy via platform webhook ──► Render/Railway
                                         │
                                         ▼
                              Neon/Supabase PostgreSQL (managed)
```
- Local dev: `docker-compose up` runs Postgres + backend together; frontend runs separately via `vite dev` against the local backend
- Secrets (DB URL, JWT signing key, OAuth client secret, email provider key) injected via the hosting platform's secret manager, never committed
- Goal: fastest path to a working, publicly reachable link for early reviews (PRD §10, decision 5)

### 13.2 Phase 2 — self-managed Linux VM + Nginx (Module 17)

**Provisioning:**
- Oracle Cloud Free Tier ARM instance (Ubuntu), always-free tier
- SSH key-based access only; disable password authentication in `sshd_config`
- Firewall (`ufw` or Oracle Cloud security list): allow only 22 (SSH), 80 (HTTP → redirect to HTTPS), 443 (HTTPS)

**Application layer:**
- Docker + Docker Compose on the VM running: FastAPI backend container, PostgreSQL container (or stay on managed Neon/Supabase if preferred — either is fine, PRD leaves this open), Redis container
- Nginx installed directly on the VM host (not containerized, simpler cert renewal), configured as a reverse proxy:
  ```
  server {
      listen 443 ssl;
      server_name api.yourdomain.com;
      ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
      ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-Proto $scheme;
      }

      location /ws/ {
          proxy_pass http://127.0.0.1:8000;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection "upgrade";
      }
  }
  server {
      listen 80;
      server_name api.yourdomain.com;
      return 301 https://$host$request_uri;
  }
  ```
- SSL via Certbot (Let's Encrypt), auto-renewal via systemd timer/cron
- FastAPI container binds to `127.0.0.1:8000` only — never exposed directly to the internet, Nginx is the only public entry point

**CI/CD update:**
```
GitHub Actions
   │  lint + pytest
   ├──► Frontend build ──► deploy ──► Vercel  (unchanged)
   └──► Backend: build Docker image, push to a registry (or build on the VM),
        SSH into the VM (deploy key stored as a GitHub secret),
        `docker compose pull && docker compose up -d`,
        health-check the /health endpoint post-deploy
```

**Why this split (frontend stays managed, backend moves to self-managed):** keeps frontend deployment simple and fast (Vercel's git-push-to-deploy is hard to beat) while putting the hands-on Linux/networking learning value where it matters most — SSH access, reverse proxy configuration, and certificate management are the parts of "deployment" a managed platform normally hides entirely (PRD §6).

---

## 14. Key Design Trade-offs

| Decision | Chosen approach | Rejected alternative | Why |
|---|---|---|---|
| Version history | Linear snapshots | Git-style branching/merge | Branching adds real diff/merge complexity for limited teaching value at this scope (PRD §10.1) |
| Freshness detection | Rule-based on timestamps | LLM-based content diffing | Deterministic, explainable, doesn't depend on external AI availability for a core feature |
| AI integration | Two narrow agents, direct DB read access | MCP / general tool-calling framework | Agents only need internal data APIFlow already owns; MCP is for connecting to external systems, unjustifiable overhead here (PRD §10.4) |
| Testing Agent scope | Reports only, no corrective action | Autonomous agent that retries/fixes issues | Keeps behavior explainable and bounded for a capstone timeline; corrective automation is a research-grade problem (PRD §10.3) |
| Send Request | Backend proxy | Direct browser → target API | Avoids CORS/IP exposure; makes execution server-verifiable, which freshness scoring and the Testing Agent both depend on |
| Multi-tenancy | Shared DB, `workspace_id` scoping | Schema-per-tenant | Simpler for this scale (2–10 people per workspace); schema-per-tenant is operational overhead with no benefit here |
| Access token storage | In-memory (JS variable/context) | localStorage | Reduces XSS token-theft surface; refresh token in httpOnly cookie instead |
| Backend hosting sequencing | Managed platform (Phase 1) → self-managed Linux VM + Nginx (Phase 2) | Self-managed from day one, or managed throughout | Fast, low-risk demo link early; hands-on Linux/networking skill added once the product itself is stable (PRD §10.5) |

---

## 15. Cross-References

- **What to build and when:** `PRD.md` (full scope), `Phase1_Part1_PRD.md` (first increment)
- **Task breakdown / execution checklist:** `Tasks.md`
