FROM python:3.12-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app app

COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts/docker-start.sh ./scripts/docker-start.sh

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && chmod +x /app/scripts/docker-start.sh \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["./scripts/docker-start.sh"]
