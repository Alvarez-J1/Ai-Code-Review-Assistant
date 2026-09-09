# Deployment Guide

This project is split into three deployable pieces:

- Next.js frontend
- FastAPI backend
- PostgreSQL database

The app does not require one specific hosting provider. A practical portfolio deployment is:

- Frontend: Vercel
- Backend: Render, Railway, Fly.io, or a small VM/container host
- Database: managed PostgreSQL from Neon, Supabase, Render Postgres, Railway, or similar

## Backend

Set these environment variables on the backend host:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
CORS_ALLOWED_ORIGINS=https://your-frontend.example
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=2000
GITHUB_TOKEN=
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_API_VERSION=2026-03-10
GITHUB_TIMEOUT_SECONDS=20
GITHUB_MAX_FILES=3000
```

Build command:

```bash
python -m pip install .
```

Migration command:

```bash
alembic upgrade head
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
```

Run migrations as an explicit release step or as part of a reviewed container entrypoint. Do not rely on SQLAlchemy `create_all()` in production.

## Frontend

Set these environment variables on the frontend host:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-backend.example/api
API_INTERNAL_BASE_URL=https://your-backend.example/api
```

Build command:

```bash
npm ci
npm run build
```

Start command for a Node host:

```bash
npm run start
```

For Vercel, use the standard Next.js framework preset and set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend API base URL.

## CORS

The backend must allow the deployed frontend origin:

```text
CORS_ALLOWED_ORIGINS=https://your-frontend.example
```

For preview deployments, add each preview origin only if you are comfortable allowing that preview to call the backend.

## Database

Use a managed PostgreSQL database for production-like deployments. Store the connection string in `DATABASE_URL`; do not commit it. If the password contains special characters, URL-encode it in the connection string.

## Demo Data

Seed demo reviews only in demo or staging environments:

```bash
python -m app.scripts.seed_demo_data
```

The seed command does not call OpenAI or GitHub and is idempotent for its fixed demo review IDs.
