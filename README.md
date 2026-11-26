# InstaPilot AI — Multi-Account Instagram AI Agent

Production-ready, multi-account Instagram AI Agent platform built with **Next.js (TypeScript + Tailwind)**, **FastAPI**, **LangGraph**, **PostgreSQL + pgvector**, and **Redis**.

## Documentation

All architecture, database, API, security, and roadmap specifications live in [`docs/planning/`](docs/planning/MASTER_IMPLEMENTATION_CHECKLIST.md).

## Quick Start (Phase 1)

1. Copy `.env.example` to `.env` and fill in your `GEMINI_API_KEY` / `GROQ_API_KEY`.
2. Start PostgreSQL (`pgvector`) and Redis:
   ```bash
   docker compose up -d
   ```
3. Backend (`backend/`): create a virtualenv, install `requirements.txt`, and run:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. Frontend (`frontend/`): install packages and run:
   ```bash
   npm install
   npm run dev
   ```
