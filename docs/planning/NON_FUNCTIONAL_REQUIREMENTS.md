# InstaPilot AI — Non-Functional Requirements

## 1. Performance & Latency

- **NFR-01 (Webhook Ack):** Webhook `POST` endpoint must validate signature, enqueue job, and return HTTP `200` within **< 500 ms** (well under Meta's timeout thresholds) to prevent duplicate retries.
- **NFR-02 (AI Response Time):** End-to-end background processing (retrieval + LLM + send) should target **< 5 seconds** with cloud APIs and **< 15 seconds** with local Ollama (hardware-dependent).
- **NFR-03 (Dashboard UI):** Initial page load **< 2s**; inbox thread switching **< 300ms** via indexed PostgreSQL queries and client caching.
- **NFR-04 (Vector Search):** `pgvector` HNSW index queries filtered by `instagram_account_id` must execute in **< 50ms** for up to 100k chunks per workspace.

## 2. Scalability & Concurrency

- **NFR-05 (Multi-Account Concurrency):** Background workers must process messages across multiple Instagram accounts concurrently without head-of-line blocking (one slow account or rate-limited account must not stall others).
- **NFR-06 (Horizontal Worker Scaling):** Workers must be stateless so additional worker processes can be spun up against the same Redis + PostgreSQL instance as account volume grows.
- **NFR-07 (Rate-Limit Compliance):** Per-account Redis token-bucket rate limiters must throttle outbound Meta API calls to stay safely below Meta's per-account limits (e.g., 750 private replies/hr, 300 text DMs/sec, dynamic BUC limits).

## 3. Reliability & Fault Tolerance

- **NFR-08 (24/7 Background Operation):** Backend API and worker processes run independently of the browser; closing the dashboard has zero impact on message ingestion or AI responses.
- **NFR-09 (Idempotency):** Duplicate Meta webhook deliveries (same `mid` or `comment_id`) must be deduplicated cleanly so customers never receive duplicate AI replies.
- **NFR-10 (Retries & Dead-Letter Queue):** Transient failures (Meta 5xx, LLM timeout) retry with exponential backoff + jitter (max 3–5 attempts); permanent failures move to a failed-job log and trigger an operator notification.
- **NFR-11 (Graceful Degradation):** If the LLM provider is unreachable, incoming messages are still saved to the Unified Inbox and flagged for human handling.

## 4. Security & Privacy

- **NFR-12 (Tenant & Account Isolation):** Zero cross-workspace or cross-account data leakage in SQL queries, vector retrieval, Redis keys, or SSE streams.
- **NFR-13 (Encryption at Rest):** OAuth access tokens must be encrypted at rest using **AES-256-GCM / Fernet** with a key managed outside the database.
- **NFR-14 (Transport Security):** TLS 1.2+ required for all production endpoints (Meta webhooks require valid HTTPS).
- **NFR-15 (Auditability):** Every tool execution, manual override, token refresh, and account connection/disconnection is recorded with actor, timestamp, and metadata.

## 5. Maintainability & Portability

- **NFR-16 (Provider Abstraction):** LLM and embedding providers must be swappable via configuration (Ollama, OpenAI, Gemini, Groq) without changing LangGraph business logic.
- **NFR-17 (Schema Migrations):** All database changes must be versioned via **Alembic** migrations.
- **NFR-18 (Local Dev Parity):** Entire stack (Postgres+pgvector, Redis, Ollama, FastAPI, Worker, Next.js) must run locally via `docker-compose` + local dev scripts at **$0 cost**.
