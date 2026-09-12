# AI Code Review Assistant
AI Code Review Assistant is a full-stack developer tool for reviewing pasted `git diff` output or GitHub pull requests. It combines deterministic static checks with structured OpenAI review, stores each completed review in PostgreSQL, and presents results in a polished Next.js interface. Built to be easy to demo, easy to run locally, and clear enough for recruiters or interviewers to understand quickly.

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/8990254b-eacf-4895-b5df-a3c419071355" />

## Features

- Review pasted unified diffs from the browser
- Review public GitHub pull request URLs, with optional token support for higher API limits
- Parse, normalize, preprocess, and chunk changed files before AI analysis
- Run deterministic checks for debug statements, secrets, broad exceptions, TODO/FIXME comments, and weak test signals
- Request structured LLM findings through Pydantic-validated OpenAI output
- Deduplicate overlapping deterministic and AI findings
- Persist review sessions and findings in PostgreSQL
- Browse recent reviews and reopen stored results
- Filter findings by severity, category, and file without refetching
- Seed realistic demo reviews without calling OpenAI or GitHub
- Run the full stack with Docker Compose

## Tech Stack

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS, Vitest, React Testing Library
- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, httpx
- AI: OpenAI SDK with structured Pydantic output
- External API: GitHub REST API
- Database: PostgreSQL
- Local runtime: Docker Compose or separate Python/Node processes

## Architecture

```mermaid
flowchart LR
    UI[Next.js App Router UI] --> API[FastAPI JSON API]
    API --> D[Unified Diff Parser]
    API --> GH[GitHub REST API]
    GH --> N[GitHub Patch Normalizer]
    N --> D
    D --> P[Review Pipeline]
    P --> PP[Preprocessing + Chunking]
    PP --> DC[Deterministic Checks]
    PP --> AI[OpenAI Structured Review]
    DC --> AG[Finding Aggregation]
    AI --> AG
    AG --> DD[Deduplication]
    DD --> R[Risk Calculation]
    R --> DB[(PostgreSQL)]
    DB --> API
    API --> UI
```

## Project Structure

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    scripts/
    services/
  alembic/
  tests/
  Dockerfile
frontend/
  app/
  components/
  lib/
  test/
  types/
  Dockerfile
docs/
  deployment.md
  images/
docker-compose.yml
```

## How The Review Pipeline Works

1. The API receives either a pasted diff or a GitHub PR URL.
2. GitHub PRs are fetched through the GitHub REST API and normalized into unified diff-like input.
3. The diff parser extracts files, hunks, changed lines, statuses, and language metadata.
4. Preprocessing skips binary/generated/dependency files and splits large changes into review chunks.
5. Deterministic checks produce fast local findings for common issues.
6. The OpenAI reviewer asks for structured findings for each prepared chunk.
7. Pydantic validates model output before it enters the application pipeline.
8. Deduplication removes overlapping findings.
9. The backend sorts findings, calculates risk, persists results, and returns a typed response.

## GitHub Integration

GitHub PR review accepts URLs like:

```text
https://github.com/owner/repository/pull/123
```

Public PRs work without OAuth. If `GITHUB_TOKEN` is configured, the backend adds an authorization header to GitHub API calls. Tokens are never returned to the frontend or persisted.

GitHub-origin review pages link findings back to the PR page. Line-specific GitHub links are not generated yet because stable GitHub diff anchors require metadata that is not currently persisted.

## Deterministic Vs AI Analysis

Deterministic checks are local rules for obvious or high-signal issues. AI analysis is used for contextual review comments that benefit from understanding surrounding code. Both paths return the same `ReviewFinding` shape, and the UI exposes the `source` field as `deterministic` or `ai`.

## Structured LLM Output

The backend uses the official OpenAI SDK and asks for an `AIReviewOutput` that Pydantic validates. Malformed model output is discarded for that chunk instead of crashing the whole review.

LangChain is not used because the current workflow is a focused single-step structured review. It can be reconsidered later for multi-step orchestration, tool routing, or retrieval.

## Database And Persistence

PostgreSQL stores:

- Review session ID, type, status, risk level, summary, counts, timestamps
- GitHub repository and PR metadata when applicable
- Finding file path, line range, category, severity, title, explanation, suggestion, confidence, and source

Raw pasted diffs and raw GitHub patches are not persisted. This keeps storage smaller and avoids retaining source code unnecessarily.

## Local Setup

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Local URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://127.0.0.1:8000/api/health`
- Backend docs: `http://127.0.0.1:8000/api/docs`

## Docker Setup

Copy the root env example and edit values as needed:

```powershell
Copy-Item .env.example .env
```

Start the full stack:

```powershell
docker compose up --build
```

Services:

- `postgres`: PostgreSQL 16 with a persistent named volume
- `backend`: FastAPI container that runs `alembic upgrade head` before starting Uvicorn
- `frontend`: production-style Next.js standalone runtime
- `seed-demo`: optional profile for inserting demo reviews

Seed demo data after the stack is healthy:

```powershell
docker compose --profile seed run --rm seed-demo
```

Then open `http://localhost:3000/reviews`.

## Environment Variables

Root `.env.example` is intended for Docker Compose. Backend and frontend examples are also provided for split local development.

Backend:

```text
APP_ENV=development
DATABASE_URL=postgresql+psycopg://ai_review_app:replace-with-local-postgres-password@localhost:5432/ai_code_review
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=2000
GITHUB_TOKEN=
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_API_VERSION=2026-03-10
GITHUB_TIMEOUT_SECONDS=20
GITHUB_MAX_FILES=3000
```

Frontend:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
API_INTERNAL_BASE_URL=http://127.0.0.1:8000/api
```

Compose also uses:

```text
POSTGRES_DB=ai_code_review
POSTGRES_USER=ai_review_app
POSTGRES_PASSWORD=replace-with-local-postgres-password
POSTGRES_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

Do not commit real API keys, GitHub tokens, database URLs, or `.env` files.

## Migrations

Alembic is the schema management path.

Local:

```powershell
cd backend
alembic upgrade head
```

Docker:

```text
backend/scripts/docker-start.sh
```

The Docker backend entrypoint runs migrations explicitly before Uvicorn starts. SQLAlchemy `create_all()` is used only inside tests with an in-memory SQLite database.

## Demo Data

Optional demo data lives in:

```text
backend/app/scripts/seed_demo_data.py
```

Run locally after migrations:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.scripts.seed_demo_data
```

The seed command inserts:

- one GitHub-style review
- one pasted-diff review
- high, medium, and low severity findings
- security, bug, testing, performance, edge-case, and readability categories
- findings across multiple files

Seeded summaries and titles are marked with `[Demo]`. The command uses fixed review IDs and skips existing rows, so it is safe to rerun.

## Testing

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm.cmd run test
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd audit
```

Frontend tests use Vitest, React Testing Library, jsdom, and mocked API calls. They cover empty diff validation, invalid GitHub PR input, API error rendering, findings filtering, zero-findings state, and review summary rendering.

## API Endpoints

- `GET /api/health`
- `POST /api/reviews/diff`
- `POST /api/reviews/github`
- `GET /api/reviews/{review_id}`
- `GET /api/reviews?limit=20&offset=0`

## Security And Privacy

- API keys and GitHub tokens are loaded from environment variables only.
- GitHub tokens are never logged, returned, or stored.
- Raw source diffs and raw GitHub patches are not persisted.
- GitHub/API/database failures are translated to safe user-facing messages.
- Frontend errors are normalized and do not render raw exception objects.
- CORS is environment-driven and should be limited to known frontend origins.

## Limitations

- The project is not a replacement for human code review.
- AI findings may be incomplete or occasionally incorrect.
- Line-specific GitHub links are intentionally avoided until stable diff anchors or commit metadata are persisted.
- There is no authentication, multi-user isolation, billing, or team management.
- Screenshots are documented but not committed until real demo captures are taken.

## Future Improvements

- Add real portfolio screenshots from seeded data.
- Add deployed demo URLs after hosting is configured.
- Add line-accurate GitHub links using persisted commit/file metadata.
- Add lightweight end-to-end smoke tests for the Docker stack.
- Add optional auth only if the app becomes a hosted multi-user service.

## License

MIT. See [LICENSE](LICENSE).
