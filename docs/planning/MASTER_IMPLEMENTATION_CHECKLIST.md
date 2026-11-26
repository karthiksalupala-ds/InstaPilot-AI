# InstaPilot AI — Master Implementation Checklist

Use this checklist to track execution once Phase 1 is authorized.

## Phase 0: Planning & Approval
- [x] Verify Meta Instagram API docs (OAuth, scopes, webhooks, 24h/7d windows, rate limits)
- [x] Generate all 15 planning documents in `docs/planning/`
- [ ] **User reviews & approves unresolved architectural decisions**

## Phase 1: Project Setup & Dashboard UI Shell
- [x] Initialize `frontend/` (Next.js, TypeScript, Tailwind CSS)
- [x] Initialize `backend/` (Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy async, Alembic)
- [x] Create `docker-compose.yml` (Postgres 16 + pgvector, Redis 7)
- [x] Build 12-module dashboard layout & navigation shell

## Phase 2: Authentication & Multi-Tenant Database
- [x] Implement all 15+ SQLAlchemy models & initial Alembic migration
- [x] Implement Argon2id auth + JWT/cookie sessions
- [x] Implement Workspace & RBAC (`owner`, `admin`, `operator`, `viewer`)
- [x] Add cross-workspace isolation unit/integration tests

## Phase 3: Instagram OAuth & Account Connections
- [ ] Create Meta Developer App & configure Instagram Login OAuth
- [x] Implement OAuth authorize/callback + 60-day long-lived token exchange
- [x] Implement AES-256-GCM token encryption & `/subscribed_apps` call
- [x] Implement ARQ daily token refresh cron (>24h old & <14d remaining)
- [ ] Wire Instagram Account Management UI

## Phase 4: Webhook Integration & Message Processing
- [x] Implement `GET/POST /webhooks/instagram` with HMAC-SHA256 check
- [x] Implement Redis deduplication (`mid` / `comment_id`) & ARQ ingestion
- [x] Implement customer/conversation upsert & 24h window tracking
- [x] Implement Redis Pub/Sub -> SSE `/events/stream`

## Phase 5: AI Agent Engine & Tool Calling
- [x] Implement configurable LLM factory 
- [x] Build LangGraph workflow (Intent -> Escalation -> RAG -> Tools -> Guardrail -> Mode Router -> Log)
- [x] Implement 8 validated tools with server-side account scoping
- [x] Wire Agent Configuration UI + Sandbox Preview + Activity Logs

## Phase 6: Knowledge Base & Conversation Memory
- [x] Implement KB ingestion (manual text, FAQ, policies, products, PDF, SSRF-safe URLs)
- [x] Implement chunking + embedding + `pgvector` HNSW search
- [x] Implement rolling `conversations.ai_summary` memory
- [x] Wire Knowledge Base & Products UI

## Phase 7: Unified Inbox
- [x] Wire 3-column Unified Inbox to live APIs & SSE
- [x] Implement manual reply, Approval Mode approve/edit/reject, Manual Mode suggestions
- [x] Implement 24h window guard, human handoff, and conversation-level AI pause

## Phase 8: CRM, Leads & Automation Rules
- [x] Implement Leads CRUD, notes, follow-up reminders, and Kanban/table UI
- [x] Implement Automation Rules engine (DM & comment keyword triggers -> public reply / 7d private DM)

## Phase 9: Analytics, Activity Logs & Notifications
- [x] Implement Analytics aggregation endpoints & charts
- [x] Implement searchable Activity Logs UI
- [x] Implement Notifications center & real-time alerts

## Phase 10: Security Testing & Deployment
- [x] Run security audit (isolation, encryption, SSRF, HMAC, rate limits)
- [x] Configure GitHub Actions CI/CD
- [x] Deploy to production HTTPS host & verify 24/7 background operation
- [ ] Prepare Meta App Review (if opening beyond app testers)
