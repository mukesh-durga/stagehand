# Stagehand API — production image.
# Build context must be this directory (apps/api):
#   docker build -t stagehand-api apps/api
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: psycopg2-binary ships wheels, but keep curl for container debugging.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Application code + migrations + startup script.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY start.sh ./start.sh

# Run as a non-root user.
RUN chmod +x ./start.sh \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Startup (migrations + uvicorn) is baked into start.sh, so Render needs NO custom
# Docker Command — leave that field blank. $PORT is injected by the host.
CMD ["./start.sh"]
