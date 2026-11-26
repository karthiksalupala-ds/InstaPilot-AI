# InstaPilot AI — Security Design

## 1. Threat Model & Security Principles

InstaPilot AI handles sensitive OAuth tokens for brand Instagram accounts, private customer DMs, and autonomous AI tool execution. Security is built around **zero cross-account leakage**, **least privilege**, and **defense in depth**.

## 2. Authentication & RBAC

- **Password Hashing:** Argon2id (via `argon2-cffi` / `passlib`) with per-user salt.
- **Session / JWT:** Short-lived JWT access tokens (15 min) + rotated refresh tokens (HTTP-only, `Secure`, `SameSite=Lax` cookies in browser).
- **Workspace RBAC Matrix:**

| Action | `owner` | `admin` | `operator` | `viewer` |
| :--- | :---: | :---: | :---: | :---: |
| Manage workspace & members | Yes | Yes | No | No |
| Connect/disconnect IG accounts | Yes | Yes | No | No |
| Configure AI Agent & Tools | Yes | Yes | No | No |
| Edit Knowledge Base & Products | Yes | Yes | Yes | No |
| Reply / Approve / Handoff in Inbox | Yes | Yes | Yes | No |
| Manage Leads & Notes | Yes | Yes | Yes | No |
| View Analytics & Logs | Yes | Yes | Yes | Yes |

## 3. Data & Account Isolation

- **Workspace Isolation:** Every authenticated endpoint resolves `workspace_id` from `workspace_members` and injects it into all SQL `WHERE` clauses (plus optional PostgreSQL RLS).
- **Account-Level Isolation:** Every AI agent invocation, RAG vector query, Redis cache key (`ratelimit:{ig_account_id}`, `dedup:{ig_account_id}:{mid}`), and SSE channel (`workspace:{workspace_id}`) is strictly keyed.
- **Prompt Injection Defense:** Customer DMs are wrapped in clear untrusted-user delimiters (`<customer_message>`) in LangGraph prompts, never concatenated into system instructions.

## 4. OAuth Token & Secret Management

- **No Password Storage:** Never ask for or store Instagram passwords.
- **Encryption at Rest:** `oauth_tokens.encrypted_access_token` is encrypted using **AES-256-GCM** (or `cryptography.fernet`) with `TOKEN_ENCRYPTION_KEY` stored in environment/secrets manager—never in the database or Git.
- **Key Rotation Support:** Version prefix on ciphertext (e.g., `v1:<ciphertext>`) allows seamless key rotation.
- **API Redaction:** Tokens are never returned in API responses, logs, or error traces.

## 5. Webhook Security & Input Validation

- **HMAC Verification:** Every `POST /api/v1/webhooks/instagram` request is verified against `META_APP_SECRET` using `X-Hub-Signature-256` with constant-time comparison (`hmac.compare_digest`). Requests failing verification return `401/403` and are logged.
- **Schema Validation:** Strict Pydantic v2 validation on all API payloads; SQLAlchemy parameterized queries prevent SQL injection.
- **File Upload Safety:** PDF uploads are size-limited (e.g., 10 MB), MIME/magic-byte verified, and parsed in a sandboxed/non-executing parser (`pypdf` / `pymupdf`) without executing embedded scripts.
- **SSRF Protection on URL Ingestion:** Website URL ingestion blocks private/loopback IP ranges (`127.0.0.0/8`, `10.0.0.0/8`, `169.254.169.254`, `::1`) and enforces HTTP/HTTPS schemes only.

## 6. Safe AI Tool Execution

- **Allowlist Enforcement:** Tools are bound per-agent from `agents.enabled_tools`; disabled tools are never exposed to the LLM.
- **Server-Side Context Injection:** `workspace_id` and `instagram_account_id` are injected by the backend runtime—**never** passed as LLM-controlled arguments—so an agent cannot be tricked into querying another account's KB or CRM.
- **Rate Limiting:** API endpoints protected by Redis sliding-window rate limits; outbound Meta calls throttled per account.

## 7. Data Deletion & Account Disconnection

- Disconnecting an Instagram account immediately deletes `oauth_tokens` and unsubscribes webhooks.
- A workspace owner can trigger a full account data purge (hard-deleting customers, conversations, messages, KB chunks, and leads for that `instagram_account_id`) to comply with Meta Data Deletion Callback requirements.
