# InstaPilot AI — Cost Estimation

## 1. Development Phase Cost: **$0 / month**

| Component | Tool / Service | Cost |
| :--- | :--- | :--- |
| Frontend & Backend | Next.js + FastAPI + ARQ (Local) | $0 |
| Database & Vector Store | PostgreSQL 16 + `pgvector` (Docker) | $0 |
| Queue & Cache | Redis 7 (Docker) | $0 |
| AI / Embeddings | **Google Gemini / Groq API** (free tier / pay-as-you-go via API keys) | $0 (free tier) |
| HTTPS Tunnel for Webhooks | Cloudflare Tunnel (`cloudflared`) | $0 |
| Source Control & CI/CD | GitHub + GitHub Actions (public/free tier minutes) | $0 |
| Meta Instagram API | Meta for Developers App | $0 |

## 2. Production Phase Cost Breakdown

### Scenario A: Ultra-Low-Cost Managed Free Tiers + Cheap Always-On Worker (~$5–$10/mo)
- **Vercel (Next.js):** $0/mo (Hobby — private/personal use; Pro $20/mo if commercial SaaS).
- **Supabase (Postgres + pgvector):** $0/mo (Free tier: 500 MB DB, pauses after 7 days inactivity—keep active via worker queries).
- **Upstash (Redis):** $0/mo (Free tier: 10k commands/day—tune ARQ poll interval to avoid exhausting quota).
- **Fly.io / Railway / Hetzner VPS (FastAPI + Worker):** ~$5–$7/mo (needed for 24/7 always-on webhooks & background processing).
- **LLM API (e.g., Gemini Flash / Groq free tier / OpenAI `gpt-4o-mini`):** $0–$5/mo for moderate DM volume.

### Scenario B: Single All-in-One VPS (~$6–$12/mo) — Recommended
- **Hetzner Cloud (2–4 vCPU, 4–8 GB RAM):** ~€4.5–€8/mo (~$5–$9/mo). Runs Next.js, FastAPI, ARQ Worker, Postgres+pgvector, Redis, and Caddy HTTPS with **zero sleep/pause limits** and **no SaaS row/command caps**.
- **Cloudflare R2 (Backups & PDFs):** $0/mo (10 GB free).
- **LLM Inference:**
  - $0/mo if using Groq/Gemini free tiers (subject to rate limits) or local GPU machine.
  - ~$1–$10/mo pay-as-you-go for production-grade low-latency models (e.g., `gpt-4o-mini` / `gemini-2.5-flash`).

## 3. Hidden / Non-Monetary Costs to Plan For

- **Meta App Review:** Free to submit, but requires preparing screencasts, privacy policy URL, data deletion callback URL, and business verification for Advanced Access.
