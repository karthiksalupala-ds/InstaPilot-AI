# InstaPilot AI — Functional Requirements

## 1. Authentication, Workspaces & User Management

- **FR-01:** Users can register/log in securely (email + password hashed with Argon2id/bcrypt; JWT access + refresh tokens or HTTP-only secure session cookies).
- **FR-02:** System supports multiple **Workspaces**; a user can belong to one or more workspaces with role-based access (`owner`, `admin`, `operator`, `viewer`).
- **FR-03:** Workspace owners/admins can invite/manage workspace members and assign roles.
- **FR-04:** All data queries and mutations are strictly scoped to the active `workspace_id` and authorized by user role.

## 2. Instagram Account Management

- **FR-05:** Users can connect multiple Instagram Professional (Business or Creator) accounts via official Meta OAuth 2.0 flow—never by entering Instagram passwords.
- **FR-06:** Dashboard displays connection status (`connected`, `token_expiring`, `disconnected`, `error`), IG username, profile picture, account type, and last webhook/sync timestamp.
- **FR-07:** System automatically refreshes long-lived tokens before their 60-day expiration and alerts users if manual reconnection is required.
- **FR-08:** Users can disconnect an Instagram account, revoking/deleting stored OAuth tokens and optionally purging or archiving associated data.

## 3. AI Agent Management & Configuration

- **FR-09:** Each connected Instagram account automatically maps to an independent AI Agent record (`1:1` or `1:many` with one active agent per account).
- **FR-10:** Users can toggle an agent **ON/OFF** per account and set default **Automation Mode** (`auto`, `approval`, `manual`).
- **FR-11:** Users can configure per-agent:
  - Agent name & identity
  - System instructions / prompt persona
  - Tone & communication style (e.g., friendly, concise, formal, emoji usage)
  - Primary language & auto-detect language behavior
  - Enabled/disabled AI tools and per-tool constraints
  - LLM provider/model selection & temperature
  - Escalation rules (keywords, negative sentiment, low confidence threshold)
- **FR-12:** Users can test an agent in a **Sandbox Preview** inside Agent Configuration without sending real Instagram messages.

## 4. Unified Inbox

- **FR-13:** Centralized inbox showing conversations across all connected Instagram accounts in a workspace, with filters by account, status (`open`, `pending_human`, `resolved`, `snoozed`), automation mode, and unread state.
- **FR-14:** Displays full message thread (DMs and comment-originated threads), customer profile sidebar, AI-generated conversation summary, and extracted customer intent.
- **FR-15:** Operators can:
  - Send manual replies directly to Instagram.
  - Approve, edit, or reject AI-drafted replies (in **Approval Mode**).
  - Copy/use AI suggested replies (in **Manual Mode**).
  - Pause or resume AI automation at the **conversation level**.
  - Assign conversations to workspace members and mark human handoff resolved.

## 5. Knowledge Base (Account-Isolated RAG)

- **FR-16:** Each Instagram account has an isolated Knowledge Base supporting:
  - Manual text entries & FAQs
  - Structured product/service catalog items (name, description, price, availability, SKU/URL)
  - Business policies (shipping, returns, booking, hours)
  - PDF document uploads (parsed, chunked, embedded)
  - Permitted website URL ingestion (user-submitted URLs fetched & extracted cleanly)
- **FR-17:** Knowledge entries can be edited, enabled/disabled, and re-indexed; deletion immediately removes associated vector embeddings.
- **FR-18:** Retrieval strictly filters by `instagram_account_id` so one account's agent can never access another account's knowledge.

## 6. AI Agent Intelligence & Tools

- **FR-19:** Incoming messages/comments trigger a structured LangGraph reasoning workflow: intent classification -> memory & RAG retrieval -> tool selection/execution -> grounded response generation -> policy/safety check.
- **FR-20:** Supported validated tools:
  - `search_knowledge_base`
  - `search_products`
  - `get_product_details`
  - `create_lead`
  - `update_lead`
  - `get_customer_history`
  - `request_human_support`
  - `send_instagram_reply`
- **FR-21:** Grounding rule: The agent must never invent prices, stock availability, discounts, or policies not present in retrieved tool/KB data; if unknown, it asks clarifying questions or escalates to a human.

## 7. Comment Management

- **FR-22:** System receives real-time Instagram `comments` webhook events.
- **FR-23:** Based on account **Automation Rules** (e.g., keyword triggers like "price", "link", "info"), the agent can post a public comment reply and/or send a single Private Reply DM within Meta's 7-day window.

## 8. CRM & Lead Management

- **FR-24:** System automatically creates/updates `customers` records from incoming Instagram interactions.
- **FR-25:** AI or operators can create and update `leads` with interest category, lead status (`new`, `qualified`, `contacted`, `converted`, `lost`), notes, and follow-up reminders.
- **FR-26:** Lead dashboard supports filtering by Instagram account, status, date, and assignee, plus viewing full lead history.

## 9. Automation Rules

- **FR-27:** Users can define account-level rules combining triggers (new DM, comment keyword, first-time customer, off-hours), conditions (intent, sentiment), and actions (auto-reply, private reply, tag lead, assign human, pause AI).

## 10. Analytics, Activity Logs & Notifications

- **FR-28:** Analytics dashboard tracks message volume, AI resolution rate, average response time, human escalation rate, lead conversion metrics, and token/LLM usage per account.
- **FR-29:** Activity Logs (`agent_execution_logs`) provide a searchable audit trail of every AI run: input, retrieved docs, tools called, output, status, latency, and errors.
- **FR-30:** In-app notifications alert operators on human escalations, pending approvals, token expiration warnings, and webhook/API failures.
