# Stagehand worker — production image.
# Build context must be this directory (apps/worker):
#   docker build -t stagehand-worker apps/worker
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Worker code.
COPY worker ./worker

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# The worker is a long-running background process; it has no HTTP port.
# Migrations are applied by the API release step, not by the worker.
CMD ["python", "-m", "worker.main"]
