# APIFlow — Product Requirements Document (PRD)

**Tagline:** A request-first collaborative API workspace for small teams that prevents documentation drift using execution-backed living docs.

**Team:** 2 members (Backend/Auth lead + Frontend lead, roles can flex)
**Timeline:** Semester 7 (Phase 1 / MVP) + Semester 8 (Phase 2 / Enhancements)
**Domain:** Software Engineering Tools / Developer Productivity / Cloud
**SDG Alignment:** SDG 9 — Industry, Innovation and Infrastructure

---

## 1. Problem Statement

API development in small teams is fragmented across disconnected tools: Postman/Insomnia for building and testing requests, Notion/Docs for documentation, chat apps for sharing collections, and Git for tracking who-changed-what — separately from the API itself.

This fragmentation causes a specific, recurring failure: **documentation is written once and never updated as the API changes.** A request's method, params, or body can change on Monday and the docs describing it are still accurate as of last month. Nothing in the current toolchain tells a team when this has happened. Reviewers, teammates, and new joiners have no way to know whether a given piece of documentation is trustworthy without manually re-testing the endpoint themselves.

Existing platforms don't solve this well:

- **Postman/Insomnia** — strong at building/sending requests, weak at keeping docs synced to actual behavior; documentation is a separate, manually-maintained artifact.
- **Stoplight/SwaggerHub** — spec-first (OpenAPI design), which assumes teams design before they build. Most student and freelance teams do the opposite: they write endpoints first and formalize specs later, if ever.
- **Notion/Confluence** — general-purpose docs tools with zero awareness of the API's actual current state.
- **GitHub** — tracks code changes, not API behavior, and has no concept of "this endpoint's docs are stale."

**One-sentence problem statement:** *Small development teams lose trust in their own API documentation because nothing in their toolchain tells them when it has drifted out of sync with the API's actual behavior — APIFlow closes that gap with execution-backed, self-verifying docs in a single collaborative workspace.*

---

## 2. Competitive Positioning

| Category | Examples | Strength | Gap APIFlow targets |
|---|---|---|---|
| Request/collection tools | Postman, Insomnia | Mature request builder, huge ecosystem | Docs are static text, no drift awareness; heavy/enterprise-leaning for tiny teams |
| Spec-first design tools | Stoplight, SwaggerHub | Strong OpenAPI tooling | Assumes spec-first workflow; steep for teams that start from raw endpoints |
| Generic docs tools | Notion, Confluence | Flexible, familiar | Zero connection to actual API behavior |

**Differentiation thesis:** APIFlow isn't trying to out-feature Postman as a general platform. It narrows to one workflow gap — *keeping documentation trustworthy as the API evolves* — for the specific audience of small teams (2–10 people) who don't want enterprise complexity or Git-centric spec review.

---

## 3. Solution Overview

APIFlow is a web-based, team-oriented API workspace where a team can:

1. Create a **Workspace** for a project (e.g., "E-Commerce Backend")
2. Organize endpoints into **Collections** (e.g., "Users", "Orders", "Payments")
3. Build and send real HTTP requests directly in the browser (via a backend proxy)
4. Attach **living documentation** to each request that is tied to the request's actual definition and execution history — not a free-floating text block
5. See a **documentation freshness signal** per endpoint, based on when the request was last changed vs. when it was last successfully executed vs. when the docs were last updated
6. Comment and collaborate on specific endpoints
7. See linear edit history for any request or collection, with rollback
8. Get AI assistance to draft documentation and to automatically re-test a whole collection and explain what broke
9. Share everything instantly within the team — no exporting/importing files

**What APIFlow is explicitly NOT:**
- Not a project management tool (no Kanban, sprints, task assignment)
- Not a deployment platform (no CI/CD dashboards, no hosting management)
- Not a general chat tool (comments are scoped only to specific API requests)
- Not a spec-first design tool (OpenAPI import/export is supported, but the primary workflow starts from a request, not a spec)

---

## 4. Target Users

- **Primary:** Computer Science students working on team projects, freelance backend developers, small startup engineering teams (2–10 people).
- **Secondary:** QA engineers who need to test and document APIs; technical writers maintaining API docs for small teams.

**Core user pain this solves:** "Is this documentation actually still true?" — currently answerable only by manually re-testing the endpoint. APIFlow answers it visually and automatically.

---

## 5. Goals of This Project (Learning Objectives)

| Area | Specific Skill |
|---|---|
| Backend | FastAPI, REST API design, async Python |
| Database | PostgreSQL, SQLAlchemy ORM, Alembic migrations |
| Auth | JWT access + refresh tokens, OAuth2 (Google login), RBAC |
| Frontend | React, component architecture, state management, calling REST APIs |
| Realtime | WebSockets (live updates when a teammate edits a request) |
| Caching | Redis (session storage, rate limiting) |
| DevOps | Docker, Docker Compose, basic CI/CD (GitHub Actions), self-managed Linux server deployment |
| Networking / SysAdmin | SSH server access, Nginx reverse proxy configuration, HTTPS/SSL certificates (Let's Encrypt), basic firewall setup, process management on Linux |
| Testing | Backend unit/integration tests (pytest) |
| Architecture | Clean layering (routes → services → repository → DB), multi-tenant data isolation (per-workspace) |
| Product thinking | Designing a feature (freshness scoring) around a specific, evidenced workflow gap rather than feature parity |

---

## 6. Tech Stack

### Frontend
- React (Vite)
- JavaScript first; migrate select files to TypeScript in Phase 2 once comfortable
- TailwindCSS
- React Router
- Axios (TanStack Query deferred to Phase 2)

### Backend
- FastAPI (async), automatic OpenAPI docs generation
- SQLAlchemy (ORM) + Alembic (migrations)
- Pydantic (validation)

### Database
- PostgreSQL — fits the naturally structured hierarchy: workspaces → collections → requests → history

### Caching / Sessions — Phase 2
- Redis: session caching, rate-limiting the outbound request proxy, refresh-token blocklist

### Realtime — Phase 2
- WebSockets: live presence, live updates when a teammate edits/comments

### Authentication
- JWT access tokens (~15 min)
- Refresh tokens (rotated on each use, stored hashed)
- Google OAuth2 (authlib)
- RBAC scoped per-workspace: Owner, Admin, Member, Viewer

### Deployment
- Docker + Docker Compose (local dev + deployment)
- **Frontend:** Vercel (free tier)
- **Backend — Phase 1:** managed free-tier platform (Render or Railway), to get a working, demoable link in front of your review panel quickly without spending early review time on server administration
- **Backend — Phase 2:** migrated to a self-managed **Linux Virtual Machine** (Oracle Cloud Free Tier — genuinely free forever, ARM instance) running Dockerized FastAPI behind **Nginx as a reverse proxy**, with HTTPS via Let's Encrypt/Certbot
- **Database:** Neon PostgreSQL (free tier) or self-hosted PostgreSQL in Docker on the VM once migrated
- **CI/CD:** GitHub Actions — test + lint on every push (Phase 1: deploy via managed-platform webhook; Phase 2: deploy step SSHes into the VM, pulls the latest Docker image, restarts the container)

**Why migrate to a real Linux VM in Phase 2:** managed platforms hide server administration, networking, and reverse-proxy configuration entirely. Deploying to a self-managed Linux VM means actually configuring the server: SSH access, firewall rules, Nginx as a reverse proxy in front of FastAPI, SSL certificates, and process management. This is closer to how backend/platform engineers work in smaller companies without a dedicated DevOps team, and it's a genuinely rare skill among student projects — most classmates will never have configured a reverse proxy or issued an SSL certificate by hand. Sequencing it in Phase 2 avoids learning Linux administration and building the MVP under deadline pressure at the same time.

---

## 7. Feature Scope

### 7.1 MVP — Phase 1 (Semester 7)

**Module 1: Authentication**
- Signup / Login (email + password)
- Google OAuth2 login
- JWT access + refresh token flow (with rotation)
- Forgot/reset password (Resend or Brevo free tier)
- Basic profile (name, avatar)

**Module 2: Workspace**
- Create workspace
- Invite members (email invite link/token)
- Roles: Owner, Admin, Member, Viewer
- Basic settings (rename, delete)

**Module 3: Collections**
- Create / rename / delete collections
- Collections contain requests (nested)

**Module 4: API Request Builder**
- Saved request: method, URL, headers, query params, JSON body
- Send request via backend proxy
- View response: status, headers, body, time taken
- Save to collection, duplicate request

**Module 5: Environment Variables**
- Per-environment variables (Development, Production)
- `{{BASE_URL}}` reference syntax
- Switch active environment per workspace

**Module 6: Documentation (Basic) + Freshness Foundation**
- Markdown description field per request
- Auto-populated: last modified by/at, **last successfully executed at**
- **Documentation freshness indicator** (basic version): flags a request as "docs may be stale" if the request definition (method/url/params/body) has changed more recently than the description field — the foundational, rule-based version of the differentiator; refined further in Phase 2 (Module 16)

**Module 7: Search**
- Text search across collections and requests by name (full-text search deferred to Phase 2)

**Module 8: Deployment**
- Dockerized frontend + backend, deployed and publicly accessible on a managed free-tier platform (see Section 6; migrated to a self-managed Linux VM in Phase 2, Module 17)

### 7.2 Phase 2 — Semester 8 (Enhancements)

**Module 9: Comments**
- Per-request comment threads, @mentions (no notification system yet), mark resolved

**Module 10: Version History**
- Linear version snapshot per edit, diff between versions, restore previous version
- (Deliberately not branching/PR-style review — see Section 9)

**Module 11: Realtime Collaboration**
- WebSocket connection per workspace, live presence indicator, live update on edit/save

**Module 12: Redis Integration**
- Cache frequently accessed workspace/collection data
- Rate-limit the Send Request proxy
- Refresh-token blocklist for logout/revocation

**Module 13: AI Agents — Documentation & Testing (small, focused — not a headline feature)**
- **Documentation Agent:** given a saved request and its most recent response, generates a plain-English description of what the endpoint does, lists expected fields, and flags when a new response no longer matches the previously documented shape. One LLM call (free-tier provider, e.g. Groq), triggered manually or on save.
- **Testing Agent:** given a collection, re-runs every saved request, compares each response against the last-known-good ("expected") response, and produces a plain-English pass/fail report explaining what changed for any failures (e.g., "status code changed from 200 to 401 — this endpoint may now require authentication"). Effectively a smart regression-test runner with natural-language reporting — scoped deliberately to stay explainable and buildable, not a general-purpose autonomous agent.
- **Why not MCP / general-purpose agents:** both agents only need read access to APIFlow's own database (saved requests, response history) — a standard internal query, not a case for a standardized external-tool protocol like MCP. MCP is for connecting an agent to *external* systems it doesn't already control (Slack, GitHub, a filesystem it doesn't own). Left out deliberately — one well-scoped feature beats a layer that's hard to justify in a viva.

**Module 14: Import / Export**
- Import OpenAPI/Swagger JSON into a collection
- Export a collection as OpenAPI JSON or Markdown docs

**Module 15: Notifications (basic)**
- In-app notification on @mention or workspace invite

**Module 16: Documentation Drift Detection (core differentiator, full version)**
- **Freshness score** per endpoint, computed from: time since last request definition change, time since last successful execution, time since last doc update
- **Verified example** auto-generated from the most recent successful response (shown alongside the written description)
- **Drift alert**: visible badge/notification when request schema/body/params change but the description field is untouched
- **Endpoint review timeline**: single view of who changed the request definition, who last re-ran it, who last updated the docs
- **"Ready to handoff" badge**: appears once docs, a verified example, and a recent successful execution all align — signals to QA/frontend teammates that this endpoint's docs can be trusted as-is
- Deliberately rule-based on timestamps, not content diffing, for MVP simplicity (see Section 9, decision 6) — this keeps it deterministic and demoable without depending on an external LLM being available or reliable. A more sophisticated "does the description text actually match the current params" check (via the Documentation Agent in Module 13) is a possible further stretch, not a requirement.

**Module 17: Production Deployment Migration (Linux VM + Nginx)**
- Provision a Linux VM (Oracle Cloud Free Tier)
- Install Docker, migrate the existing Dockerized backend/Postgres/Redis containers to run on the VM
- Configure Nginx as a reverse proxy in front of the FastAPI container
- Set up HTTPS via Let's Encrypt/Certbot
- Configure basic firewall rules and SSH key-based access (disable password auth)
- Update GitHub Actions CI/CD to deploy via SSH to the VM instead of a managed-platform webhook

**Explicitly deferred / cut from scope (do not build unless Phase 1+2 finish early):**
- Analytics dashboard (most-used APIs, response time graphs)
- Full Swagger/OpenAPI round-trip fidelity
- Dark mode, keyboard shortcuts
- Deployment monitoring dashboard
- Full project/task management (Kanban, sprints)
- MCP (Model Context Protocol) integration — see Section 9, decision 4
- General-purpose/autonomous AI agents beyond the two scoped agents in Module 13 (e.g., a "debugging agent" or "deployment assistant" that analyzes logs and takes autonomous action) — research-grade problems, not a good fit for a bounded capstone timeline

---

## 8. Database Schema (Core Tables)

```
users
  id, email, password_hash (nullable if OAuth-only), name, avatar_url,
  created_at, is_verified

oauth_accounts
  id, user_id (FK), provider, provider_user_id

refresh_tokens
  id, user_id (FK), token_hash, expires_at, revoked, created_at

workspaces
  id, name, owner_id (FK -> users), created_at

workspace_members
  id, workspace_id (FK), user_id (FK), role (owner/admin/member/viewer), joined_at

collections
  id, workspace_id (FK), name, created_at, created_by (FK -> users)

requests
  id, collection_id (FK), name, method, url, headers (JSONB),
  params (JSONB), body (JSONB), description (text),
  created_by (FK), updated_by (FK), created_at, updated_at,
  last_verified_at (timestamp, nullable)   -- supports Module 16 freshness scoring

request_versions -- Phase 2
  id, request_id (FK), snapshot (JSONB), changed_by (FK), changed_at

environments
  id, workspace_id (FK), name

environment_variables
  id, environment_id (FK), key, value, is_secret (bool)

comments -- Phase 2
  id, request_id (FK), user_id (FK), body, resolved (bool),
  created_at, parent_comment_id (nullable, for replies)

response_history
  id, request_id (FK), status_code, response_body (JSONB),
  time_taken_ms, sent_at, sent_by (FK)
```

**Multi-tenancy approach:** shared database, `workspace_id` foreign key scoping on nearly every table. Every query filters by workspace membership — enforced at the service layer, not just the API layer, to avoid data leaks between workspaces.

**Freshness scoring** (Module 16) is computed, not stored as a separate table for MVP — it's derived at read time from `requests.updated_at`, `requests.last_verified_at`, and the description field's own last-updated timestamp. Only add a dedicated table if computing this on every read becomes a real performance problem.

---

## 9. Architecture

```
┌─────────────────┐
│   React SPA      │  (Vite, Tailwind, React Router) — deployed on Vercel
└────────┬─────────┘
         │ HTTPS (REST JSON + WebSocket)
         ▼
┌─────────────────┐
│  Nginx (reverse  │  Linux VM (Oracle Cloud Free Tier) — Phase 2 onward
│  proxy, SSL term)│  - Handles HTTPS/SSL (Let's Encrypt)
└────────┬─────────┘  - Routes traffic to the FastAPI container
         ▼            (Phase 1: this hop is a managed platform instead — see Section 6)
┌─────────────────┐
│  FastAPI Backend  │  (Dockerized, routes → services → repositories)
│  - Auth middleware (JWT verification, RBAC checks)
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌───────┐
│Postgres│ │ Redis │   (Dockerized, same VM or managed free tier)
└────────┘ └───────┘
```

**Layered backend structure (Clean Architecture-lite):**
```
app/
  api/           # route handlers (thin — request/response only, calls services)
  services/      # business logic (e.g., "can this user edit this request?",
                 #  freshness score calculation)
  repositories/  # DB queries (SQLAlchemy)
  models/        # SQLAlchemy models
  schemas/       # Pydantic request/response schemas
  core/          # config, security (JWT), dependencies
  websockets/    # Phase 2 realtime handlers
```

**Architecture note — "Send Request" feature:** The browser does not call the target API directly (CORS issues, exposes the user's IP/environment). The FastAPI backend proxies the outbound request on the user's behalf and returns the response to the frontend — the same approach Postman's cloud sync / Postman Web use. This also gives a natural place to implement rate-limiting (Redis) and response history logging, and it's what makes `last_verified_at` and the freshness score possible: every send is a real, timestamped execution record, not a self-report.

**Deployment topology note (Phase 2):** the backend, PostgreSQL, and Redis run as Docker containers on a single self-managed Linux VM, with Nginx on the same VM acting as reverse proxy and SSL termination in front of the FastAPI container. The frontend stays on Vercel throughout. This split — managed frontend hosting, self-managed backend server — is deliberate: it keeps frontend deployment simple while giving hands-on Linux/networking experience where it teaches the most.

---

## 10. Explicit Scope Decisions (Read Before Starting)

Deliberate choices to keep the project buildable by 2 students in 2 semesters. Do not silently expand scope without revisiting this document.

1. **"GitHub for APIs"** (branching, PR-style review workflows) is explicitly NOT in scope. Only simple linear version history + rollback (Module 10). Branching/merge semantics are meaningfully harder and add limited teaching value over the simpler version.
2. **TypeScript is optional, not mandatory** for MVP. Plain JavaScript is the Phase 1 default; introduce TypeScript incrementally in Phase 2.
3. **AI features are two well-scoped agents, not a general agent framework** (Module 13). A Documentation Agent and a Testing Agent, each doing one clear job with a single LLM call/loop — not an open-ended "AI does everything" system. This is not a "Generative AI" or "Agentic AI" capstone — AI supports the product, it isn't the core identity.
4. **No MCP (Model Context Protocol).** Both AI agents only need read access to APIFlow's own database — a standard internal query, not a case for a standardized external-tool protocol. MCP is for connecting an agent to *external* systems it doesn't control. Adding it here would be unjustifiable if a reviewer asks "why," so it's deliberately excluded.
5. **Backend deployment upgrades from a managed platform (Phase 1) to a self-managed Linux VM + Nginx (Phase 2), not the reverse.** This sequencing gets a working demo link fast for early reviews, then adds the hands-on Linux/networking learning value once the core product is stable.
6. **Drift detection is rule-based on timestamps, not content diffing**, for MVP simplicity. This keeps the headline differentiator deterministic, explainable, and demoable without depending on an external LLM being available or reliable. A more sophisticated content-aware check (via the Documentation Agent, Module 13) is a possible Phase 2+ stretch, not a Phase 1 requirement.
7. **No project management module** (no Kanban/sprints/tasks) — avoids duplicating Jira and keeps the identity focused: this is an API tool, not a PM tool.
8. **No deployment monitoring dashboard.** Deploying the app itself (Module 8) teaches real deployment skills; a dashboard about deployments is a separate, unrelated feature.

---

## 11. Phase Timeline (Mapped to Review Schedule)

| Review | Target Deliverable |
|---|---|
| 0th Review | This PRD, architecture diagram, tech stack justification, team roles |
| 1st Review | Auth fully working (signup/login/OAuth/JWT+refresh) + workspace creation/invites |
| 2nd Review | Collections + Request Builder (create, save, send request, view response) working end-to-end |
| 3rd Review | Environment variables + basic documentation fields + freshness indicator + search + deployed, publicly accessible MVP |
| Model Viva / Report (Sem 7 end) | Full MVP demo: create workspace → create collection → build request → send it → see response → document it, with a visible freshness signal |
| Phase 2 (Sem 8) | Comments, version history, WebSocket realtime, Redis caching, Documentation + Testing AI agents, full drift-detection suite (Module 16), migration to self-managed Linux VM + Nginx (Module 17), import/export, notifications |
| Final Review | Full production-style demo + report covering both phases, with the drift-prevention thesis as the headline differentiator |

---

## 12. Non-Functional Requirements

- Responsive UI (usable on laptop screen sizes at minimum; mobile is not a priority)
- Proper error handling and validation on every API endpoint (Pydantic schemas enforce this by default)
- Secure password hashing (bcrypt/argon2), no plaintext secrets anywhere
- Environment variables for all secrets (never hardcoded, `.env` gitignored)
- Basic logging (request logs, error logs)
- Reasonable test coverage on backend business logic (auth flow, RBAC checks, request-sending proxy, freshness score calculation) — doesn't need to be exhaustive, but should cover auth/security-critical paths

---

## 13. Team Role Suggestion

- **Member A (Backend-lead):** Auth system, database schema, API design, request-proxy logic, freshness/drift scoring logic, Redis/WebSockets in Phase 2, Linux VM + Nginx deployment migration.
- **Member B (Frontend-lead):** React app structure, request builder UI, workspace/collection UI, freshness indicator/badge UI — learning React/Tailwind from scratch, supported by Member A on API contract design so frontend work is never blocked.

Both members should understand the full stack by the end — pair on at least one feature per phase end-to-end (e.g., build "send request" together, backend + frontend) so neither is a stranger to the other half of the codebase during the viva.

---

## 14. How to Use This Document

Paste this PRD into a new conversation to begin:
1. Detailed database schema design + Alembic migration setup
2. FastAPI project scaffolding (folder structure, first auth endpoints)
3. React project scaffolding (Vite setup, first pages)
4. Step-by-step build order following the Phase 1 module list above

Recommended first build order: **Auth → Workspace → Collections → Request Builder → Send Request (proxy) → Environments → Documentation fields + basic freshness indicator → Search → Deploy.** Each step should be a working, demoable increment — don't move to the next module until the current one works end-to-end (backend + frontend + manual test).
