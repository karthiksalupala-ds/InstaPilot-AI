# InstaPilot AI — Development Roadmap

> **Rule:** Every phase builds incrementally on the previous one. No phase is marked complete without passing its testing and completion criteria.

## Phase 0: Architecture & Planning (Current Phase)
- **Objectives:** Finalize product vision, Meta API constraints, DB schema, API contracts, AI agent graph, security model, and cost plan.
- **Deliverables:** Complete 15-document planning package in `docs/planning/`.
- **Completion Criteria:** User review and explicit approval of unresolved architectural decisions.

## Phase 1: Project Setup & Dashboard UI Shell
- **Objectives:** Initialize monorepo (`frontend/` Next.js + `backend/` FastAPI), local Docker Compose (Postgres+pgvector, Redis), and build the responsive 12-module UI shell with mock/static data.
- **Dependencies:** Phase 0 approval.
- **Deliverables:** Running Next.js app, FastAPI healthcheck, `docker-compose.yml`, navigation + layout for all 12 modules.
- **Testing:** Frontend type-check (`tsc --noEmit`), build check, backend `/health` pytest.
- **Completion Criteria:** Clean local startup and navigable UI shell.

## Phase 2: Authentication & Multi-Tenant Database
- **Objectives:** Implement SQLAlchemy models, Alembic migrations for all 15+ tables, Argon2id auth, JWT/cookie sessions, workspace creation, and RBAC middleware.
- **Dependencies:** Phase 1.
- **Deliverables:** Migrated Postgres schema, `/auth/*` and `/workspaces/*` endpoints, login/register UI wired to backend.
- **Testing:** Unit tests for RBAC matrix & cross-workspace isolation (403/404 on foreign `workspace_id`).
- **Completion Criteria:** Users can register, log in, switch workspaces, and RBAC blocks unauthorized roles.

## Phase 3: Instagram OAuth & Account Connections
- **Objectives:** Implement Meta OAuth 2.0 flow, short-to-long-lived token exchange, AES-256-GCM token encryption, `/subscribed_apps`, account disconnect/purge, and scheduled token refresh job.
- **Dependencies:** Phase 2 + Meta Developer App created.
- **Deliverables:** `/instagram/oauth/*`, `/instagram/accounts/*`, ARQ token refresh cron, Accounts UI wired live.
- **Testing:** Mocked Meta OAuth & refresh unit tests; manual end-to-end connection with a test IG Professional account.
- **Completion Criteria:** Real test IG account connects, stores encrypted 60-day token, and displays live status.

## Phase 4: Webhook Integration & Message Processing
- **Objectives:** Implement `GET/POST /webhooks/instagram` with HMAC-SHA256 verification, Redis deduplication, ARQ worker ingestion, customer/conversation upserts, and SSE live push.
- **Dependencies:** Phase 3 + HTTPS tunnel (e.g., Cloudflare Tunnel / ngrok) for local webhook testing.
- **Deliverables:** Webhook receiver, ARQ worker pipeline, SSE endpoint `/events/stream`.
- **Testing:** Signature verification tests (valid/invalid), idempotency tests (duplicate `mid`), end-to-end DM webhook -> DB -> SSE.
- **Completion Criteria:** Incoming test IG DMs and comments appear in DB and trigger SSE events within 1–2s.

## Phase 5: AI Agent Engine & Tool Calling
- **Objectives:** Build LangGraph state machine (`LoadContext` -> `ClassifyIntent` -> `CheckEscalation` -> `RetrieveKnowledge` -> `ReasonAndPlanTools` -> `GroundingGuardrail` -> `RouteByAutomationMode`), Ollama + configurable LLM factory, and validated tools.
- **Dependencies:** Phase 4.
- **Deliverables:** LangGraph agent engine, 8 validated tools, Agent Configuration UI + Sandbox Preview, `agent_execution_logs`.
- **Testing:** Tool permission/isolation tests, grounding tests (refuses to invent unknown prices), sandbox E2E tests.
- **Completion Criteria:** Agent accurately processes test messages in Auto/Approval/Manual modes and logs every step.

## Phase 6: Knowledge Base & Conversation Memory
- **Objectives:** Implement account-isolated RAG pipeline (manual text, FAQs, products, policies, PDF parsing, SSRF-safe URL ingestion), chunking, embedding, `pgvector` HNSW search, and rolling conversation summaries.
- **Dependencies:** Phase 5.
- **Deliverables:** Knowledge Base APIs, ARQ ingestion worker, Products CRUD, Knowledge Base UI wired live.
- **Testing:** Cross-account RAG isolation tests (Account A never retrieves Account B chunks), PDF/URL ingestion tests.
- **Completion Criteria:** Agent answers questions accurately using uploaded PDFs/products with zero cross-account leakage.

## Phase 7: Unified Inbox
- **Objectives:** Wire the 3-column Unified Inbox to live APIs and SSE: account/status filters, manual reply via Meta Send API, Approval Mode approve/edit/reject, Manual Mode suggestions, 24h window guard, human handoff, and conversation-level AI pause.
- **Dependencies:** Phase 4, 5, 6.
- **Deliverables:** Fully functional Unified Inbox UI & backend endpoints.
- **Testing:** Integration tests for 24h window enforcement, approval flow, and live SSE message updates.
- **Completion Criteria:** Operator can monitor, approve, reply, and pause AI across multiple accounts seamlessly.

## Phase 8: CRM, Leads & Automation Rules
- **Objectives:** Wire Leads & CRM module (table/Kanban, notes, follow-up reminders), automatic lead creation via agent tools, and Automation Rules engine (comment keyword -> public reply + 7-day Private Reply DM).
- **Dependencies:** Phase 7.
- **Deliverables:** CRM APIs & UI, Automation Rules engine & UI, comment-to-DM pipeline.
- **Testing:** Rule evaluation unit tests, comment-to-private-reply integration tests.
- **Completion Criteria:** Comment triggers and lead workflows operate end-to-end automatically.

## Phase 9: Analytics, Activity Logs & Notifications
- **Objectives:** Build Analytics aggregation queries & charts, searchable Activity Logs viewer, and in-app notification center (escalations, approvals, token expiry, errors).
- **Dependencies:** Phase 8.
- **Deliverables:** Analytics, Activity Logs, and Notifications APIs + UI modules.
- **Testing:** Query accuracy tests, pagination/filtering tests.
- **Completion Criteria:** All 12 dashboard modules are live and backed by real data.

## Phase 10: Security Testing & Production Deployment
- **Objectives:** Full security audit (OWASP checks, tenant isolation pen-tests, token encryption verification), GitHub Actions CI/CD pipeline, production deployment, and Meta App Review preparation (if expanding beyond testers).
- **Dependencies:** Phase 9.
- **Deliverables:** CI/CD workflows, production deployment runbook, security test report.
- **Testing:** Full regression suite, load/rate-limit simulation, webhook replay & failure recovery tests.
- **Completion Criteria:** 24/7 production stability verified with dashboard closed.
