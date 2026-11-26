# InstaPilot AI — Deployment Strategy

## 1. Local Development Environment ($0)

- **Infrastructure:** `docker-compose.yml` running `postgres:16` (with `pgvector`), `redis:7`, and optionally `ollama`.
- **Apps:** Next.js dev server (`npm run dev`), FastAPI (`uvicorn --reload`), ARQ worker (`arq app.worker.WorkerSettings`).
- **Webhook Testing:** Free **Cloudflare Tunnel** (`cloudflared tunnel`) or `ngrok` exposing local FastAPI `/api/v1/webhooks/instagram` over HTTPS to Meta.

## 2. Production Hosting Options (Solo-Dev Friendly)

### Option A: Single-VPS Self-Hosted (Best Value & Full Control — Recommended for Private Phase)
- **Host:** 1x Linux VPS (e.g., Hetzner CX22/CX32 or DigitalOcean, 4–8 GB RAM) running Docker Compose:
  - Reverse Proxy: **Caddy** (automatic Let's Encrypt HTTPS for Meta webhooks)
  - `frontend` (Next.js)
  - `api` (FastAPI)
  - `worker` (ARQ background worker)
  - `postgres` (PostgreSQL 16 + pgvector)
  - `redis` (Redis 7)
- **LLM:** Cloud LLM API (e.g., Gemini Flash / OpenAI mini / Groq) for fast response without needing a GPU VPS, OR Ollama on a GPU machine if self-hosting models.

### Option B: Managed Free/Low-Tier Cloud Split
- **Frontend:** Vercel (Hobby/Free tier for Next.js).
- **Database:** Supabase (Free tier includes PostgreSQL + `pgvector`).
- **Redis:** Upstash Redis (Free tier, watch command limits for ARQ polling).
- **Backend + Worker:** Railway / Render / Fly.io (always-on container required for 24/7 background workers & webhook responsiveness).

## 3. GitHub Actions Role (Strict Boundary)

- **Used For:** CI tests, linting, Docker image builds/pushes, and optional scheduled maintenance pings (e.g., health check).
- **NEVER Used For:** Running the 24/7 FastAPI webhook server or background worker (GitHub Actions has cold starts, job time limits, and is not an always-on server).

## 4. Backup & Disaster Recovery

- Automated daily `pg_dump` encrypted and stored off-server (e.g., Cloudflare R2 free tier 10 GB).
- `.env` secrets and `TOKEN_ENCRYPTION_KEY` backed up securely in a password manager / secrets vault.
