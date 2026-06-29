#!/usr/bin/env bash
# Install worker deps and start the run consumer.
#
# IMPORTANT: start the worker only AFTER the API has applied migrations
# (scripts/deploy_api.sh runs `alembic upgrade head`). The worker never runs
# migrations itself, so it cannot apply destructive schema changes.
#
# Required env: DATABASE_URL (or POSTGRES_* components), REDIS_URL, CLICKHOUSE_*.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_DIR="$SCRIPT_DIR/../apps/worker"
cd "$WORKER_DIR"

echo "==> Installing worker dependencies"
pip install .

echo "==> Starting Stagehand worker"
exec python -m worker.main
