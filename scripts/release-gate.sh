#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v gitleaks >/dev/null || {
  echo "gitleaks is required for the full-history release scan." >&2
  exit 1
}

gitleaks git --redact --no-banner .
SCAN_DIR="$(mktemp -d)"
trap 'rm -rf "$SCAN_DIR"' EXIT
git ls-files --cached --others --exclude-standard -z \
  | tar --null -T - -cf - \
  | tar -xf - -C "$SCAN_DIR"
gitleaks dir --redact --no-banner "$SCAN_DIR"
pnpm install --frozen-lockfile
pnpm lint
pnpm build
uv sync --project backend --extra dev --locked
uv run --project backend python scripts/check-licenses.py
uv run --project backend ruff check backend
uv run --project backend pytest backend/tests \
  --cov=app.graph --cov=app.guardrails --cov=app.retrieval \
  --cov=app.model_routing --cov=app.mcp_tools --cov=app.evaluations \
  --cov=app.costs --cov=app.scoring --cov-report=term-missing \
  --cov-fail-under=85
POSTGRES_PASSWORD=release-check \
APP_DATABASE_PASSWORD=release-check \
C2CDIRECT_CONFIG_ENCRYPTION_KEY=release-check \
EMAIL_TOKEN_ENCRYPTION_KEY=release-check \
docker compose -f deploy/core/compose.yml config --quiet

echo "C2CDirect repository release gate passed."
