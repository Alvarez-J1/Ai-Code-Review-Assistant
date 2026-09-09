#!/usr/bin/env sh
set -eu

echo "Applying Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
