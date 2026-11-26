# InstaPilot AI — Project Vision

## 1. Executive Summary

**InstaPilot AI** is a multi-account Instagram AI Agent platform that enables an operator (and, in future SaaS releases, multiple tenant organizations) to connect multiple Instagram Professional accounts and manage them from a single centralized dashboard.

Each connected Instagram account is paired with its own **independent, strictly isolated AI agent** that:

- Understands incoming Instagram Direct Messages (DMs) and supported post/reel comments.
- Classifies customer intent and retrieves relevant context from conversation history and account-specific knowledge bases (RAG).
- Reasons over business rules and executes authorized tools (e.g., product lookup, lead creation/updating, human escalation).
- Operates 24/7 in the background via event-driven webhooks and background workers, even when the dashboard is closed.
- Respects per-account and per-conversation **Automation Modes**: **Auto**, **Approval**, and **Manual**.

## 2. Problem Statement

Managing multiple Instagram business/creator accounts manually does not scale:

1. **Fragmented Inboxes:** Switching between multiple Instagram accounts or Meta Business Suite tabs slows response times and causes missed leads.
2. **Repetitive Inquiries:** Customers repeatedly ask about pricing, availability, shipping, booking, and policies.
3. **Generic Chatbots Fail:** Rule-based auto-responders cannot understand nuance, maintain multi-turn context, or safely trigger CRM actions without hallucinating.
4. **Cross-Account Contamination Risk:** Using a single shared AI prompt or knowledge store across multiple brands/accounts risks leaking prices, tone, or customer data between accounts.

## 3. Target Users & Evolution Path

### Phase A: Private Multi-Account Operator (Initial Scope)
- **Primary User:** Solo operator / internal team managing multiple owned Instagram Professional accounts (e.g., multiple brands, niches, or client-managed pages).
- **Focus:** Zero-cost / low-cost development, fast iteration, rock-solid isolation, full auditability, and reliable 24/7 background automation.

### Phase B: Multi-Tenant SaaS Platform (Future Expansion)
- **Target Users:** Agencies, e-commerce brands, creators, and SMBs connecting their own Instagram accounts via self-serve OAuth.
- **Architectural Readiness:** Every table, API route, vector index, cache key, and background job is scoped by `workspace_id` and `instagram_account_id` from Day 1, enabling SaaS onboarding, billing, and Meta App Review expansion without rewriting the core engine.

## 4. Core Product Pillars

1. **Strict Account Isolation:** Every Instagram account has its own agent identity, system instructions, personality, language config, knowledge base, vector embeddings, conversation memory, CRM leads, automation rules, and tool permissions.
2. **Tool-Using Agentic Intelligence:** Powered by LangGraph, agents classify intent, retrieve RAG context, reason, invoke validated tools, and log every step (`agent_execution_logs`)—never inventing prices, stock, or policies.
3. **Human-in-the-Loop Control:** Seamless switching between **Auto Mode**, **Approval Mode** (human approves/edits AI drafts), and **Manual Mode** (AI suggests only), plus one-click human handoff and automation pause/resume.
4. **Official Meta API Compliance:** Built exclusively on official Meta Instagram APIs (OAuth, webhooks, Send API, Comments API) with encrypted token storage, signature verification, rate-limit handling, and zero password collection or unsupported scraping.
5. **Solo-Developer Pragmatism:** Modular monolith backend (FastAPI + worker process) + Next.js frontend + PostgreSQL/pgvector + Redis—no premature microservices.

## 5. Out of Scope (Initial Release)

- Unofficial Instagram private APIs, password-based logins, or browser-automation bots.
- Automated cold DM outreach / unsolicited spam blasts (prohibited by Meta policies).
- Full Instagram content publishing/scheduling suite (focus is messaging, comments, RAG, and CRM).
- Native mobile apps (responsive web dashboard first).
- Billing/Stripe subscription engine (deferred until SaaS phase, though workspace schema supports it).
