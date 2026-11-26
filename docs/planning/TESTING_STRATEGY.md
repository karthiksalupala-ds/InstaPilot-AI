# InstaPilot AI — Testing Strategy

## 1. Testing Pyramid

1. **Unit Tests (Fast, Isolated — `pytest` & `vitest`):**
   - LangGraph node logic with mocked LLM responses.
   - Tool validation, permission enforcement, and `instagram_account_id` scoping.
   - Meta webhook HMAC-SHA256 signature verification & payload parsing.
   - Automation rule evaluation, 24h DM window & 7d private reply window checks.
   - Encryption/decryption round-trips for OAuth tokens.
2. **Integration Tests (`pytest` + Test PostgreSQL/pgvector + Redis):**
   - Multi-tenant & multi-account isolation tests (verify Account A cannot read Account B's conversations, leads, or RAG chunks).
   - Alembic migration up/down verification.
   - Idempotency tests: sending the same webhook `mid` twice creates only 1 message and 1 agent run.
   - RAG ingestion -> chunking -> embedding -> vector retrieval accuracy.
3. **Contract & Mocked External API Tests (`respx` / `httpx` mock):**
   - Simulate Meta Graph API `200`, `429` rate limit, `401` expired token, and `500` transient errors.
   - Verify Redis rate limiter and ARQ retry/backoff behavior.
4. **End-to-End (E2E) Tests (`Playwright`):**
   - Login -> Connect Account (mocked OAuth callback) -> Upload KB -> Configure Agent -> Simulated Webhook -> Verify Unified Inbox SSE update -> Approve Draft.

## 2. CI Automation (GitHub Actions)

Every Pull Request runs:
- **Backend:** `ruff` (lint), `mypy` (type check), `pytest` (unit + integration against ephemeral Postgres+pgvector & Redis service containers).
- **Frontend:** `eslint`, `tsc --noEmit`, `next build`.
