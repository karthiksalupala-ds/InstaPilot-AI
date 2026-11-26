# InstaPilot AI — API Specification

## 1. Conventions

- **Base URL:** `/api/v1`
- **Auth:** `Authorization: Bearer <JWT>` (or HTTP-only secure cookie) for all dashboard routes; `X-Hub-Signature-256` for Meta webhooks.
- **Tenant Header / Scoping:** `X-Workspace-Id: <uuid>` validated against `workspace_members` for every authenticated request.
- **Response Envelope:** Standard JSON with Pydantic validation; errors follow RFC 7807-style `{ "error": { "code": "...", "message": "...", "details": ... } }`.

## 2. Endpoint Groups

### 2.1 Auth & Workspaces
- `POST /auth/register` — Create user + default workspace (disabled or invite-only in private mode).
- `POST /auth/login` — Issue access + refresh tokens.
- `POST /auth/refresh` — Rotate refresh token.
- `GET /auth/me` — Current user profile & workspace memberships.
- `GET /workspaces` / `POST /workspaces` — List or create workspaces.
- `GET /workspaces/{id}/members` / `POST /workspaces/{id}/members` / `PATCH /workspaces/{id}/members/{member_id}` — Role management (`owner`, `admin`, `operator`, `viewer`).

### 2.2 Instagram Accounts & OAuth
- `GET /instagram/oauth/authorize` — Generates signed Meta OAuth URL with state token (`workspace_id`, `user_id`, CSRF nonce).
- `GET /instagram/oauth/callback` — Exchanges code -> short-lived token -> 60-day long-lived token, encrypts & stores token, subscribes `/subscribed_apps`.
- `GET /instagram/accounts` — List connected IG accounts with health, token expiry, and agent status.
- `PATCH /instagram/accounts/{account_id}` — Toggle `is_agent_enabled`, default `automation_mode`.
- `POST /instagram/accounts/{account_id}/refresh-token` — Manual token refresh trigger.
- `DELETE /instagram/accounts/{account_id}` — Disconnect account, revoke/purge encrypted tokens, optionally purge data.

### 2.3 Meta Webhooks (Unauthenticated by JWT; Verified by HMAC)
- `GET /webhooks/instagram` — Meta verification challenge (`hub.mode`, `hub.verify_token`, `hub.challenge`).
- `POST /webhooks/instagram` — Verifies `X-Hub-Signature-256`, deduplicates, enqueues ARQ job, returns `200 OK` in `< 500ms`.

### 2.4 AI Agents & Configuration
- `GET /accounts/{account_id}/agent` — Fetch agent config.
- `PATCH /accounts/{account_id}/agent` — Update identity, system instructions, personality, language, LLM provider/model, enabled tools, escalation config.
- `POST /accounts/{account_id}/agent/sandbox` — Run dry-run simulation against the agent + account RAG without sending to Instagram.

### 2.5 Unified Inbox & Conversations
- `GET /inbox/conversations` — Paginated list across workspace, filterable by `instagram_account_id`, `status`, `unread_only`, `assigned_user_id`, `search`.
- `GET /inbox/conversations/{conv_id}` — Thread messages + customer profile + AI summary + pending drafts.
- `POST /inbox/conversations/{conv_id}/messages` — Send manual operator reply via Meta Send API.
- `POST /inbox/conversations/{conv_id}/approve-draft` — Approve (and optionally edit) AI draft in Approval Mode and send.
- `POST /inbox/conversations/{conv_id}/reject-draft` — Reject AI draft.
- `PATCH /inbox/conversations/{conv_id}` — Update `status`, `assigned_user_id`, `is_ai_paused`, `automation_mode_override`.
- `GET /events/stream` — Server-Sent Events (SSE) stream for live messages, approvals, notifications, and agent logs.

### 2.6 Knowledge Base & Products
- `GET /accounts/{account_id}/knowledge/documents` — List KB documents & indexing status.
- `POST /accounts/{account_id}/knowledge/documents` — Create manual text, FAQ, policy, or website URL entry (triggers async chunk+embed job).
- `POST /accounts/{account_id}/knowledge/upload-pdf` — Multipart PDF upload (triggers async parse+chunk+embed job).
- `DELETE /accounts/{account_id}/knowledge/documents/{doc_id}` — Delete doc & cascade delete embeddings.
- `POST /accounts/{account_id}/knowledge/search` — Test RAG retrieval scores.
- `GET/POST/PATCH/DELETE /accounts/{account_id}/products` — CRUD for structured product catalog.

### 2.7 CRM, Leads & Automation Rules
- `GET /leads` / `POST /leads` / `PATCH /leads/{lead_id}` — Account-filterable lead management & reminders.
- `GET/POST/PATCH/DELETE /accounts/{account_id}/automation-rules` — Manage keyword/event rules.

### 2.8 Analytics, Logs & Notifications
- `GET /analytics/overview` — Aggregated KPIs (messages, AI resolution %, avg response time, escalations, leads, token usage) filterable by account & date range.
- `GET /logs/agent-executions` — Paginated audit log of LangGraph runs.
- `GET /notifications` / `PATCH /notifications/{id}/read` — Operator alerts.
