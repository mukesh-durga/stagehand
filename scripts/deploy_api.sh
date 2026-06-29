#!/usr/bin/env bash
# Install API deps, apply migrations, and start the API.
# Used by managed platforms or for a manual VM deploy. Run from repo root or
# anywhere — paths are resolved relative to this script.
#
# Required env: DATABASE_URL (or POSTGRES_* components), REDIS_URL, CLICKHOUSE_*.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$SCRIPT_DIR/../apps/api"
cd "$API_DIR"

echo "==> Installing API dependencies"
pip install .

echo "==> Applying database migrations (alembic upgrade head)"
alembic upgrade head

echo "==> Starting API on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
