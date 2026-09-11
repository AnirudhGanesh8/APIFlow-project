# APIFlow — Tasks.md

Execution-level checklist. Companion to `PRD.md` (what/why) and `System-Design.md` (how). Work top to bottom — don't start a module until the previous one is demoable end-to-end (backend + frontend + manual test), per PRD §14.

Checkbox convention: `[ ]` not started, `[~]` in progress, `[x]` done. Each module lists Backend, Frontend, and Tests separately so work can be split between the two members without blocking each other (per PRD §13 — agree on the API contract from System-Design §5 first, then build in parallel).

---

## Module 0: Repo & Environment Setup
*(Precedes Phase1_Part1_PRD.md scaffolding — one-time setup)*

- [x] Create monorepo or two-repo structure: `/backend`, `/frontend`
- [x] Backend: `pyproject.toml`/`requirements.txt` — fastapi, uvicorn, sqlalchemy, alembic, pydantic, pydantic-settings, python-jose or pyjwt, passlib[bcrypt], authlib, httpx, pytest, pytest-asyncio
- [x] Frontend: `npm create vite@latest` (React template), install tailwindcss, react-router-dom, axios
- [x] `docker-compose.yml`: postgres service + backend service, shared network
- [x] `.env.example` (backend): `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `RESEND_API_KEY` (or Brevo), `FRONTEND_URL`
- [x] `.gitignore` for both projects (`.env`, `node_modules`, `__pycache__`, `.venv`)
- [x] GitHub repo created, both members added, branch protection on `main` (optional but recommended)
- [x] Alembic initialized (`alembic init`), configured to read `DATABASE_URL` from settings

---

## Module 1: Authentication
*(Full detail in `Phase1_Part1_PRD.md` — summarized here for tracking)*

### Backend
- [x] `models/user.py`, `models/oauth_account.py`, `models/refresh_token.py` per System-Design §4.2
- [x] Alembic migration for `users`, `oauth_accounts`, `refresh_tokens`
- [x] `core/security.py`: password hash/verify (bcrypt), JWT encode/decode, refresh token generation (secure random) + hashing
- [x] `core/config.py`: settings via pydantic-settings
- [x] `core/deps.py`: `get_current_user` dependency (validates access token)
- [x] `schemas/auth.py`: `UserCreate`, `UserLogin`, `TokenPair`, `UserOut`
- [x] `repositories/user_repository.py`: create, get_by_email, get_by_id
- [x] `services/auth_service.py`: signup, login, refresh (with rotation + reuse-detection per System-Design §6.1), logout, forgot/reset password
- [x] `api/auth.py`: wire up all 9 endpoints from System-Design §5.1
- [x] Google OAuth2 via authlib: `/auth/google/login`, `/auth/google/callback`
- [x] Forgot/reset password: integrate Resend or Brevo free-tier email send, short-lived reset token (JWT or random+hash, stored or stateless)
- [x] Set refresh token as httpOnly/Secure/SameSite cookie on login/refresh; access token returned in JSON body only

### Frontend
- [x] `api/auth.js`: axios calls for all auth endpoints
- [x] `context/AuthContext.jsx`: holds `user`, `accessToken` in memory; `login()`, `logout()`, `signup()` methods
- [x] Axios interceptor: on 401, call `/auth/refresh` once, retry original request; on refresh failure, log out
- [x] `pages/Signup.jsx`, `pages/Login.jsx` — forms with validation, error display
- [x] `pages/ForgotPassword.jsx`, `pages/ResetPassword.jsx`
- [x] "Continue with Google" button → redirects to `/auth/google/login`
- [x] `components/ProtectedRoute.jsx` — redirects to `/login` if not authenticated
- [x] `pages/Dashboard.jsx` — placeholder, just proves auth works end-to-end
- [x] On app load: attempt silent refresh (call `/auth/refresh`) to restore session before rendering protected routes

### Tests
- [x] pytest: signup (success, duplicate email), login (success, wrong password, unknown email)
- [x] pytest: refresh rotation (old token invalidated), refresh reuse triggers full revocation
- [x] pytest: `/auth/me` requires valid token, rejects expired/invalid token
- [x] Manual: full flow in browser — signup → refresh page → still logged in → logout

**✅ Milestone check (maps to 1st Review, partially):** signup/login/OAuth/JWT+refresh fully working.

---

## Module 2: Workspace

### Backend
- [ ] `models/workspace.py`, `models/workspace_member.py` (role enum: owner/admin/member/viewer)
- [ ] Alembic migration
- [ ] `schemas/workspace.py`: `WorkspaceCreate`, `WorkspaceOut`, `InviteCreate`, `MemberOut`
- [ ] `repositories/workspace_repository.py`
- [ ] `services/workspace_service.py`: create (creator = owner), list-for-user, rename, delete (owner-only), invite generation, invite acceptance, role change
- [ ] `core/deps.py`: add `require_role(workspace_id, minimum)` dependency per System-Design §6.2 permission matrix
- [ ] `api/workspaces.py`: all endpoints from System-Design §5.2
- [ ] Invite token: signed/random token with expiry, single-use or capped-use

### Frontend
- [ ] `pages/WorkspaceList.jsx` — list + "create workspace" modal
- [ ] `pages/WorkspaceSettings.jsx` — rename, delete, member list with role dropdowns (Admin+ only)
- [ ] Invite flow UI: generate invite link, copy-to-clipboard; `pages/AcceptInvite.jsx` for the invited user
- [ ] Route guarding: workspace routes check membership (via API 403 → redirect)

### Tests
- [ ] pytest: only members can view; only Admin+ can invite/change roles; only Owner can delete
- [ ] pytest: invite accept adds `workspace_members` row with correct role
- [ ] Manual: create workspace → invite second (test) account → accept → see it in both accounts

**✅ Milestone check (2nd half of 1st Review):** workspace creation/invites working alongside Auth.

---

## Module 3: Collections

### Backend
- [ ] `models/collection.py`
- [ ] Alembic migration
- [ ] `schemas/collection.py`
- [ ] `repositories/collection_repository.py`
- [ ] `services/collection_service.py`: create/rename/delete, all workspace-membership-checked
- [ ] `api/collections.py`

### Frontend
- [ ] `pages/Workspace.jsx` — sidebar listing collections, "new collection" action
- [ ] Rename/delete UI (inline edit or modal)

### Tests
- [ ] pytest: CRUD respects role permissions (Member+ create/rename, Admin+ delete)
- [ ] Manual: create/rename/delete a collection inside a workspace

---

## Module 4: API Request Builder + Send Request Proxy

### Backend
- [ ] `models/request.py` (per System-Design §4.2 — includes `updated_at`, `description_updated_at`, `last_verified_at`; also add `expected_response_shape` column now even though it's unused until Module 13/16, to avoid a later migration)
- [ ] `models/response_history.py` (include `triggered_by` enum column — `user`/`testing_agent`, default `user` — per System-Design §4.2, even though `testing_agent` isn't produced until Module 13)
- [ ] Alembic migration
- [ ] `schemas/request.py`: `RequestCreate`, `RequestUpdate`, `RequestOut` (include `freshness` block — see Module 6)
- [ ] `repositories/request_repository.py`, `repositories/response_history_repository.py`
- [ ] `services/request_service.py`: CRUD, duplicate; on update, bump `updated_at`, and bump `description_updated_at` only if `description` field changed
- [ ] Proxy logic: `send_request()` — resolve `{{VARS}}` (Module 5 dependency, can stub initially), build `httpx` outbound call, enforce timeout (~15s) and response body size cap (~1MB), basic SSRF guard (reject loopback/link-local/private target IPs per System-Design §7)
- [ ] On send: write `response_history` row (`triggered_by=user`); if 2xx, update `requests.last_verified_at`
- [ ] `api/requests.py`: all endpoints from System-Design §5.4

### Frontend
- [ ] `pages/RequestBuilder.jsx`: method dropdown, URL bar, tabs for Headers/Params/Body
- [ ] `components/ResponseViewer.jsx`: status, headers, body (pretty-printed JSON), time taken
- [ ] Save / duplicate actions
- [ ] Request list within a collection (sidebar)
- [ ] Loading state while send is in-flight; error state for network/timeout failures

### Tests
- [ ] pytest: send proxies correctly (mock outbound with `httpx` mock/respx), records response_history, updates `last_verified_at` only on 2xx
- [ ] pytest: SSRF guard rejects a private-IP target
- [ ] pytest: `updated_at` vs `description_updated_at` bump logic (change body only → `description_updated_at` unchanged; change description only → it does)
- [ ] Manual: build a request against a real public test API (e.g. httpbin.org), send it, see the response

**✅ Milestone check (2nd Review):** Collections + Request Builder create/save/send/view-response working end-to-end.

---

## Module 5: Environment Variables

### Backend
- [ ] `models/environment.py`, `models/environment_variable.py`
- [ ] Alembic migration
- [ ] `schemas/environment.py`
- [ ] `repositories/environment_repository.py`
- [ ] `services/environment_service.py`: CRUD variables, mask `is_secret` values in read responses
- [ ] Variable resolution function: substitute `{{KEY}}` in `url`/`headers`/`params`/`body` before proxying — wire into `request_service.send_request()`
- [ ] `api/environments.py`

### Frontend
- [ ] `pages/Environments.jsx`: manage environments + variables per workspace
- [ ] Environment switcher (dropdown, workspace-scoped active environment)
- [ ] `{{VAR}}` autocomplete/highlight in Request Builder URL/headers/body fields (nice-to-have, not blocking)
- [ ] Secret values masked in UI (show/hide toggle)

### Tests
- [ ] pytest: variable substitution correctly resolves `{{BASE_URL}}` etc.; missing variable handled gracefully (clear error, not a crash)
- [ ] pytest: `is_secret` values never appear in plain in list responses (masked)
- [ ] Manual: switch environment, confirm the same request hits a different base URL

---

## Module 6: Documentation (Basic) + Freshness Foundation

### Backend
- [ ] Confirm `description`, `description_updated_at`, `last_verified_at` are already on `requests` (Module 4) — no new table
- [ ] `services/freshness_service.py`: implement Phase 1 rule from System-Design §10 — `stale = updated_at > description_updated_at`
- [ ] Wire `freshness` block into `RequestOut` schema / `GET /requests/{id}` response
- [ ] Markdown storage as plain text (rendering happens client-side)

### Frontend
- [ ] Description field: Markdown textarea + rendered preview toggle in Request Builder
- [ ] Display "last modified by / at" (already tracked via `updated_by`/`updated_at`)
- [ ] Freshness badge/indicator on the request (e.g. "docs may be stale" banner) driven by the `freshness.status` field
- [ ] Freshness indicator also visible at a glance in the collection's request list (small icon/dot)

### Tests
- [ ] pytest: freshness_service unit tests — fresh case, stale case, edge case (never verified)
- [ ] Manual: edit a request's URL without touching the description → confirm "stale" badge appears; then update the description → badge clears

**✅ Milestone check (contributes to 3rd Review):** basic docs + freshness indicator live.

---

## Module 7: Search

### Backend
- [ ] `api/search.py`: `GET /workspaces/{ws_id}/search?q=` — `ILIKE` match across collection + request names, workspace-membership-scoped
- [ ] Basic relevance ordering (exact match > prefix match > substring), or simplest-first (alphabetical) if time-constrained

### Frontend
- [ ] Search bar in workspace header, debounced input
- [ ] Results dropdown/panel grouped by Collections / Requests, click-through to the item

### Tests
- [ ] pytest: search only returns results from workspaces the user is a member of
- [ ] Manual: search partial names, confirm correct matches

---

## Module 8: Deployment (Phase 1 — managed platform)

- [ ] Backend `Dockerfile` (multi-stage if needed), confirm runs via `docker-compose up` locally
- [ ] Frontend build (`npm run build`) verified, deployed to Vercel
- [ ] Backend deployed to Render or Railway (free tier); fallback Oracle Cloud Free Tier if limits hit
- [ ] Managed Postgres provisioned (Neon or Supabase free tier); run Alembic migrations against it
- [ ] Environment variables configured in hosting platform's secret manager (not committed)
- [ ] CORS configured on backend to allow the deployed frontend origin
- [ ] GitHub Actions workflow: `lint + pytest` on every push; deploy step on merge to `main`
- [ ] Smoke test the full flow on the live deployed URL: signup → workspace → collection → request → send → see response

**✅ Milestone check (3rd Review):** deployed, publicly accessible MVP; Model Viva demo script ready (create workspace → collection → request → send → document it, freshness signal visible).

*Note: this deployment is intentionally the low-effort managed-platform version. It gets replaced (not just extended) by Module 17 in Phase 2 — see System-Design §13 for why the sequencing is deliberate.*

---

# Phase 2 (Semester 8)

## Module 9: Comments
- [ ] Backend: `models/comment.py`, migration, `services/comment_service.py`, `api/comments.py` (`POST/GET /requests/{id}/comments`, `PATCH /comments/{id}/resolve`)
- [ ] @mention parsing (basic — regex/string match on `@name`, no push notifications yet, ties into Module 15)
- [ ] Frontend: comment thread panel on Request Builder, reply threading via `parent_comment_id`, resolve toggle
- [ ] Tests: comment CRUD respects workspace membership; resolve permission check

## Module 10: Version History
- [ ] Backend: `models/request_version.py`, migration; on every `request` update, write a snapshot row (in `request_service.update()`, after the existing definition-vs-description diff logic)
- [ ] `api/versions.py`: list versions, diff (`GET /requests/{id}/versions/diff?from=&to=`), restore
- [ ] Diff logic: simple field-by-field JSON diff, no fancy text-diffing needed
- [ ] Frontend: version timeline UI, diff viewer, restore button (with confirmation)
- [ ] Tests: snapshot created on every relevant update; restore correctly reverts fields and creates a new version (not a destructive rollback)

## Module 11: Realtime Collaboration
- [ ] Backend: `websockets/workspace_ws.py` per System-Design §8 — connection auth (JWT check on upgrade), in-memory room registry per `workspace_id`
- [ ] Broadcast events: `presence.join/leave`, `request.updated`, `comment.created`, `test_run.completed` (used by Module 13's Testing Agent once built)
- [ ] Frontend: WS client in `AuthContext` or a dedicated `WorkspaceSocketContext`; presence avatars; live-refresh affected views on `request.updated`
- [ ] Tests: connection rejects invalid/expired token; broadcast reaches only same-workspace sockets (not cross-workspace leakage)

## Module 12: Redis Integration
- [ ] Add Redis service to `docker-compose.yml`
- [ ] `core/rate_limit.py`: token bucket or sliding window on `/requests/{id}/send`, keyed per user
- [ ] Separate, stricter rate-limit bucket for `/collections/{id}/ai/test-run` (Module 13) — one run fans out into many sends + LLM calls, per System-Design §11
- [ ] Cache layer for workspace/collection reads (System-Design §11), explicit invalidation on writes
- [ ] Refresh-token blocklist in Redis, checked in `auth_service.refresh()` alongside DB check
- [ ] Tests: rate limit triggers correctly after threshold; cache invalidates on write; blocklisted token rejected

## Module 13: AI Agents — Documentation Agent & Testing Agent
*(Replaces the earlier single "AI Assistant" concept — see System-Design §9 for full design and PRD §10 decisions 3–4 for why this stays two narrow agents, no MCP)*

### Backend — shared
- [ ] `services/ai/llm_client.py`: thin wrapper around Groq (or equivalent free-tier provider) — build prompt, call API, return text; single responsibility, no framework
- [ ] Graceful failure handling: LLM call failure/timeout returns a clear "AI assistance unavailable" response, never blocks the underlying request/collection feature
- [ ] `test_runs` and `test_run_results` models + Alembic migration (System-Design §4.2)
- [ ] Add `expected_response_shape` usage now (column already added in Module 4) — helper to compute top-level key/type shape from a JSON response body

### Backend — Documentation Agent
- [ ] `services/ai/documentation_agent.py`
- [ ] `generate-description`: build prompt from request definition + most recent `response_history`, call `llm_client`, return draft — does NOT write to `requests.description` directly
- [ ] `shape-check`: compare latest response's top-level shape against `expected_response_shape`, return match/mismatch + plain-English note if mismatched
- [ ] `api/ai.py`: `POST /requests/{id}/ai/generate-description`, `GET /requests/{id}/ai/shape-check`

### Backend — Testing Agent
- [ ] `services/ai/testing_agent.py`
- [ ] `run_collection_tests(collection_id, user)`: create `test_runs` row (`status=running`), sequentially call existing `request_service.send_request()` for every request in the collection (`triggered_by=testing_agent`) — reuse the Module 4 proxy path, no new outbound-call logic
- [ ] Per-request comparison: against `expected_response_shape` if set, else previous `response_history` entry; on mismatch, one LLM call → plain-English explanation written to `test_run_results.explanation`
- [ ] On completion: one summarizing LLM call → `test_runs.summary`; set `status=completed`; broadcast `test_run.completed` over WebSocket if Module 11 is live
- [ ] Explicitly reports only — never edits a request definition or retries with different parameters (System-Design §9.2 scope boundary — keep this in code review, not just docs)
- [ ] `api/ai.py`: `POST /collections/{id}/ai/test-run` (async, returns `test_run_id`), `GET /test-runs/{id}` (poll status + results)

### Frontend
- [ ] "Generate description" button in Request Builder → shows draft in an editable field, user must explicitly save
- [ ] Shape-check indicator/button, shows plain-English mismatch note if present
- [ ] "Run tests" button on a Collection view → kicks off a test run, shows running/polling state
- [ ] Test run results view: per-request pass/fail, explanation on failure, overall summary at the top
- [ ] Loading and error states for all of the above (LLM calls can be slow or fail)

### Tests
- [ ] pytest: mock the LLM client for both agents; verify graceful degradation when it fails/times out
- [ ] pytest: Testing Agent correctly reuses the send proxy and tags `response_history.triggered_by=testing_agent`
- [ ] pytest: Testing Agent never mutates a request's definition fields (only reads + writes to `test_runs`/`test_run_results`)
- [ ] pytest: RBAC — running tests requires Member+ per System-Design §6.2 permission matrix
- [ ] Manual: generate a description for a real request, edit it, save; run a full collection test, confirm pass/fail + explanations look sensible; force a failure (e.g. change a request's URL to something that 404s) and confirm the Testing Agent's explanation is coherent

## Module 14: Import / Export
- [ ] Backend: `POST /workspaces/{ws_id}/import` — parse OpenAPI/Swagger JSON, map paths/methods into collections+requests
- [ ] `GET /workspaces/{ws_id}/export` — serialize a collection to OpenAPI JSON and/or Markdown
- [ ] Frontend: file upload for import, download button for export
- [ ] Tests: round-trip a small OpenAPI spec (import then export), verify core fields preserved; malformed spec handled with a clear error

## Module 15: Notifications (Basic)
- [ ] Backend: `models/notification.py`, triggered on @mention (Module 9) and workspace invite (Module 2)
- [ ] `GET /notifications`, `PATCH /notifications/{id}/read`
- [ ] Frontend: notification bell + dropdown, unread count badge
- [ ] Tests: notification created on mention/invite; marking read updates state correctly

## Module 16: Documentation Drift Detection (full version)
- [ ] Extend `freshness_service.py` from the Phase 1 binary rule to the scored version in System-Design §10
- [ ] `last_verified_at` + most recent `response_history.status_code` factored into `freshness_score`
- [ ] `ready_for_handoff` computed flag per System-Design §10 formula
- [ ] "Verified example" — surface the most recent successful `response_history` entry alongside the description in the UI
- [ ] Drift alert: banner/notification when definition changes post-date the description (extends Module 6's basic badge)
- [ ] Endpoint review timeline: combine `request_versions` (Module 10) + `response_history` + `description_updated_at` into one chronological view
- [ ] Confirm `freshness_score`/`ready_for_handoff` logic has NO dependency on the AI agents (Module 13) or LLM availability — keep it purely rule-based per System-Design §10; the Documentation Agent's `shape-check` stays a separate, opt-in signal a user can consult
- [ ] Frontend: "Ready to handoff" badge component, verified-example panel, review timeline view
- [ ] Tests: unit tests for the full scoring formula across fresh/stale/never-verified/failed-last-send cases; this is the headline differentiator — give it real test coverage, not just happy-path

## Module 17: Production Deployment Migration (Linux VM + Nginx)
*(New — replaces Module 8's managed-platform backend hosting; see System-Design §13.2 for full config detail)*

### Provisioning
- [ ] Provision an Oracle Cloud Free Tier ARM VM (Ubuntu)
- [ ] Generate/attach an SSH keypair; confirm key-based login works
- [ ] Disable password authentication in `sshd_config`; restart `sshd`
- [ ] Configure firewall (`ufw` and/or Oracle Cloud security list): allow only 22, 80, 443
- [ ] Install Docker + Docker Compose on the VM

### Application migration
- [ ] Move `docker-compose.yml` (backend + Postgres + Redis, or backend-only if staying on managed Postgres) to run on the VM
- [ ] Confirm the FastAPI container binds to `127.0.0.1:8000` only (not exposed publicly)
- [ ] Point `DATABASE_URL` at either the VM-local Postgres container or the existing managed Neon/Supabase instance (either is acceptable per PRD)
- [ ] Run Alembic migrations against the target DB from the VM

### Nginx + HTTPS
- [ ] Install Nginx directly on the VM host
- [ ] Register/point a domain or subdomain at the VM's IP
- [ ] Write the Nginx reverse-proxy config per System-Design §13.2 (HTTP→HTTPS redirect, `/` → FastAPI, `/ws/` → FastAPI with Upgrade headers)
- [ ] Install Certbot, issue a Let's Encrypt certificate, confirm HTTPS works
- [ ] Set up Certbot auto-renewal (systemd timer or cron), test a dry-run renewal

### CI/CD update
- [ ] Add a GitHub Actions deploy step: SSH into the VM using a deploy key stored as a GitHub secret
- [ ] Deploy step runs `docker compose pull && docker compose up -d` (or builds fresh on the VM if not using a registry)
- [ ] Add a post-deploy health check (`GET /health` or similar) that fails the workflow if the backend doesn't come back up
- [ ] Update frontend's API base URL to the new domain; confirm Vercel deploy still points correctly

### Tests
- [ ] Manual: full smoke test against the new domain — signup → workspace → collection → request → send → freshness badge → AI agents (Module 13) → response
- [ ] Manual: confirm WebSocket connections (Module 11) work through the Nginx `/ws/` proxy, not just plain REST
- [ ] Manual: kill and restart the backend container, confirm Nginx returns a clean error (not a broken connection) and recovers once the container is back
- [ ] Confirm old managed-platform backend URL (Module 8) is decommissioned/redirected so there's one canonical live URL for the Final Review

**✅ Milestone check (Final Review infrastructure):** production-style, self-managed deployment live with HTTPS; this is the deliverable that demonstrates the Linux/networking learning objective from PRD §5.

---

## Final Review Prep
- [ ] Full regression pass: repeat the Model Viva demo script end-to-end on the Module 17 (Linux VM) deployment
- [ ] Confirm demo highlights the drift-prevention thesis explicitly (not just feature-listing): show a request going stale, then show it becoming "ready for handoff" again
- [ ] Confirm demo includes both AI agents distinctly: Documentation Agent drafting a description, Testing Agent catching a deliberately broken endpoint with a coherent explanation
- [ ] Report covering both phases, referencing `PRD.md` positioning (§2) and `System-Design.md` trade-offs (§14) for the "why these decisions" narrative — including why AI agents don't use MCP (§9) and why deployment moved from managed to self-managed (§13)
