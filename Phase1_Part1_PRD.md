# APIFlow — Phase 1, Part 1: Project Scaffolding + Auth Module

> Working spec for this build increment only. Paste this into GitHub Copilot Chat (VS Code) as context before generating code. Full product PRD and repositioning notes exist separately — this doc scopes *only* the first buildable slice.

## 0. Positioning (for context, not for this sprint)
Repositioned identity per competitive review: *"A request-first collaborative API workspace for small teams that prevents documentation drift using execution-backed living docs."* This doesn't change anything in Part 1 — auth is auth regardless of positioning — but keep naming (e.g. avoid generic "Postman clone" language in code comments/READMEs) consistent with this framing going forward.

## 1. Goal of This Increment
Stand up two empty-but-connected projects (FastAPI backend, React frontend) and implement a fully working authentication system. This is the foundation everything else (workspaces, collections, requests) will sit on top of. **Definition of done:** a user can sign up, log in (email/password or Google), receive a working access+refresh token pair, stay logged in across a page refresh, log out, and reset a forgotten password — tested manually end-to-end.

## 2. In Scope
### 2.1 Backend scaffolding
```
app/
  api/            # route handlers (auth.py)
  services/       # auth_service.py — business logic
  repositories/   # user_repository.py — DB queries
  models/         # SQLAlchemy: User, OAuthAccount, RefreshToken
  schemas/        # Pydantic: UserCreate, UserLogin, TokenPair, UserOut
  core/           # config.py, security.py (hashing, JWT), deps.py
  main.py
alembic/
docker-compose.yml   # postgres + backend
.env.example
```

### 2.2 Frontend scaffolding
```
src/
  pages/          # Signup.jsx, Login.jsx, ForgotPassword.jsx, ResetPassword.jsx, Dashboard.jsx (placeholder)
  api/            # axios instance + auth.js API calls
  context/        # AuthContext.jsx (stores user, access token in memory)
  components/     # ProtectedRoute.jsx
  App.jsx / main.jsx
```
Vite + React Router + Tailwind, JavaScript only (no TS yet, per PRD §10, decision 2).

### 2.3 Database tables (only these three for now)
- `users`: id, email (unique), password_hash (nullable), name, avatar_url, is_verified, created_at
- `oauth_accounts`: id, user_id (FK), provider, provider_user_id
- `refresh_tokens`: id, user_id (FK), token_hash, expires_at, revoked, created_at

### 2.4 API endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | Email + password signup |
| POST | `/auth/login` | Email + password login → access + refresh token |
| POST | `/auth/refresh` | Exchange refresh token for new pair (rotation) |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/google/login` | Redirect to Google OAuth consent |
| GET | `/auth/google/callback` | Handle callback, create/link user, issue tokens |
| POST | `/auth/forgot-password` | Send reset email (Resend/Brevo free tier) |
| POST | `/auth/reset-password` | Set new password via token |
| GET | `/auth/me` | Return current user from access token |

### 2.5 Auth mechanics
- Access token: JWT, ~15 min expiry, sent in `Authorization: Bearer`
- Refresh token: opaque, stored hashed in DB, rotated on every use, revocable
- Passwords: bcrypt or argon2
- Google OAuth2: `authlib`
- Route protection: FastAPI dependency validates JWT and injects `current_user`

## 3. Explicitly Out of Scope (this increment)
- Workspaces, collections, requests, environments — nothing beyond `users`/`oauth_accounts`/`refresh_tokens` tables
- RBAC roles (Owner/Admin/Member/Viewer) — irrelevant until workspaces exist
- Redis, WebSockets, comments, version history, AI features — all Phase 2
- Deployment to Vercel/Render — later module (Module 8)
- Any documentation-drift / freshness-score features from the repositioning — those depend on requests existing first

## 4. Acceptance Checklist
- [ ] `docker-compose up` brings up Postgres + backend locally
- [ ] Alembic migration creates `users`, `oauth_accounts`, `refresh_tokens`
- [ ] Signup → login → `/auth/me` returns correct user (manual curl/Postman test)
- [ ] Refresh token rotation works (old token invalid after use)
- [ ] Google OAuth login creates a user and logs them in
- [ ] Forgot/reset password flow sends and honors a real email link
- [ ] React app: signup/login forms call the API, store access token, redirect to a placeholder dashboard on success
- [ ] Refreshing the page keeps the user logged in (silent refresh via `/auth/refresh`)
- [ ] Basic pytest coverage: signup, login, invalid login, token refresh, RBAC-free access control on `/auth/me`

## 5. Suggested Build Order Within This Part
1. Backend scaffolding + Docker Compose + Alembic init
2. `users` model + signup/login endpoints (password only, no OAuth yet)
3. JWT access/refresh issuing + `/auth/me` + `/auth/refresh`
4. Frontend scaffolding + Signup/Login pages wired to the API
5. Google OAuth2 (backend + "Continue with Google" button)
6. Forgot/reset password flow
7. Pytest coverage for the above
