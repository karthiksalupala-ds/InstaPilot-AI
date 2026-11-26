# InstaPilot AI — UI/UX Specification

## 1. Design Language & Layout

- **Stack:** Next.js (App Router), TypeScript, Tailwind CSS, Lucide Icons, shadcn/ui-style accessible primitives.
- **Theme:** Clean, high-contrast SaaS aesthetic (dark/light mode support), responsive sidebar navigation, workspace switcher in top-left, notification bell & account health indicator in top bar.
- **Navigation Architecture:** Persistent left sidebar grouping the 12 core modules.

## 2. The 12 Dashboard Modules

| # | Module | Core Capabilities & UI Components |
| :--- | :--- | :--- |
| **1** | **Overview Dashboard** | Workspace KPI cards (Active Accounts, Messages Today, AI Resolution %, Pending Approvals, New Leads), live activity feed, quick account ON/OFF toggles, error alerts. |
| **2** | **Instagram Account Management** | "Connect Instagram Account" OAuth CTA, account cards showing `@handle`, connection status badge, token expiry countdown, webhook health, default Automation Mode selector, disconnect/purge action. |
| **3** | **AI Agent Management** | Grid/list of all account-bound agents showing status (ON/OFF), LLM model, active tools count, 24h runs, error rate, and quick jump to Configuration. |
| **4** | **Agent Configuration** | Split-pane editor: Left = Identity, System Instructions, Personality/Tone, Language, LLM Provider/Model, Tool Permissions, Escalation Rules. Right = **Live Sandbox Chat Preview** (test RAG + tools without sending to IG). |
| **5** | **Unified Inbox** | 3-column layout: (1) Filterable conversation list (by IG account, status, unread, assignee); (2) Chat thread with manual composer, **Approve/Edit/Reject** banner for Approval Mode, **Use Suggestion** for Manual Mode, 24h window countdown; (3) Customer & AI Summary sidebar (profile, tags, lead status, pause/resume AI toggle, human handoff). |
| **6** | **Knowledge Base** | Account selector + tabs for **Manual Text / FAQs**, **Products Catalog**, **Policies**, **PDF Uploads**, **Website URLs**. Shows indexing status (`indexed`, `pending`, `failed`) and a **Test Retrieval** search bar. |
| **7** | **Automation Rules** | Rule builder list per account: Trigger (`DM`, `Comment Keyword`, `First Contact`) -> Conditions -> Actions (`Auto Reply`, `Private Reply DM`, `Create Lead`, `Assign Human`). |
| **8** | **Leads & CRM** | Filterable table + Kanban view by Lead Status (`new`, `qualified`, `contacted`, `converted`, `lost`), account filter, follow-up reminder dates, inline notes, link to source conversation. |
| **9** | **Analytics** | Charts for message volume over time, AI vs Human resolution split, average response latency, escalation reasons, lead conversion funnel, and LLM token usage per account. |
| **10** | **Activity Logs** | Searchable audit table of `agent_execution_logs`: timestamp, IG account, customer, intent, tools called (expandable JSON), grounding status, latency, tokens, and errors. |
| **11** | **Workspace Settings** | Workspace name, default timezone, LLM provider API keys (masked), webhook/integration diagnostics. |
| **12** | **User Management** | Workspace members list, invite member, role selector (`owner`, `admin`, `operator`, `viewer`), remove access. |

## 3. Real-Time UX Patterns

- **SSE Live Updates:** New incoming DMs, pending approval drafts, and escalation alerts update the Unified Inbox badge and thread in real time without page refresh.
- **Optimistic UI:** Sending a manual reply or approving a draft shows immediate `sending...` state and updates to `sent` or `failed` (with retry button) upon Meta API confirmation.
