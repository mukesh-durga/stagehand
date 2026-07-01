#!/bin/sh
# Container startup for the Stagehand API.
#
# Baked into the image so Render (and other Docker hosts) need NO custom Docker
# Command — leave that field blank and the image runs this. Applies DB migrations
# then starts uvicorn. $PORT is injected by the host; defaults to 8000 locally.
set -e

echo "==> Applying database migrations (alembic upgrade head)"
python -m alembic upgrade head

echo "==> Starting API on port ${PORT:-8000}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
