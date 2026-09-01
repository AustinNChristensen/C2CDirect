#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_dir/deploy/core/compose.yml"
smoke_env="$(mktemp)"
project="c2cdirect-smoke-$RANDOM"
python_bin="$(command -v python3 || command -v python)"
core_port="$($python_bin -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
base_url="http://127.0.0.1:$core_port"
backup_dir="$(mktemp -d)"
backup_file=""

cleanup() {
  if [[ "${KEEP_SMOKE:-false}" == "true" ]]; then
    echo "Smoke environment retained: $project ($smoke_env)"
    return
  fi
  docker compose -p "$project" --env-file "$smoke_env" -f "$compose_file" down -v >/dev/null 2>&1 || true
  [[ -n "$backup_file" && -f "$backup_file" ]] && unlink "$backup_file"
  rmdir "$backup_dir" 2>/dev/null || true
  rm -f "$smoke_env"
}
trap cleanup EXIT

secret="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')"
{
  echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
  echo "APP_DATABASE_PASSWORD=$(openssl rand -hex 24)"
  echo "AUTH_DISABLED_FOR_LOCAL_DEV=true"
  echo "C2CDIRECT_CONFIG_ENCRYPTION_KEY=$secret"
  echo "EMAIL_TOKEN_ENCRYPTION_KEY=$secret"
  echo "SEARXNG_SECRET=$(openssl rand -hex 24)"
  echo "C2CDIRECT_MODEL_PROVIDER=deterministic"
  echo "CORE_PORT=$core_port"
} > "$smoke_env"

docker compose -p "$project" --env-file "$smoke_env" -f "$compose_file" up -d --build
healthy=false
for _ in $(seq 1 120); do
  if curl -fsS "$base_url/api/health" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done
if [[ "$healthy" != "true" ]]; then
  docker compose -p "$project" --env-file "$smoke_env" -f "$compose_file" ps
  docker compose -p "$project" --env-file "$smoke_env" -f "$compose_file" logs --tail=100
  exit 1
fi

curl -fsS -X PUT "$base_url/api/v1/profile" \
  -H 'content-type: application/json' \
  --data '{"display_name":"Core Smoke","headline":"Independent engineer","bio":"","target_roles":["AI Engineer"],"seniority_levels":["senior"],"min_rate":100,"target_rate":125,"locations":["Remote"],"work_modes":["remote"],"core_skills":["TypeScript"],"ai_skills":["Python"],"require_c2c":true,"onboarding_completed":true}' >/dev/null

run_id="$(curl -fsS -X POST "$base_url/api/v1/acquisition-runs" \
  -H 'content-type: application/json' \
  --data '{"kind":"import","request":{"jobs":[{"source":"smoke","title":"AI Engineer","company":"Example","description":"Remote C2C contract role using TypeScript and Python with a disclosed rate of $130 per hour.","location":"Remote","rate_min":120,"rate_max":140}]}}' \
  | "$python_bin" -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

for _ in $(seq 1 60); do
  status="$(curl -fsS "$base_url/api/v1/acquisition-runs/$run_id" | "$python_bin" -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [[ "$status" == "completed" ]] && break
  [[ "$status" == "failed" ]] && exit 1
  sleep 1
done
[[ "$status" == "completed" ]]
curl -fsS "$base_url/api/v1/jobs" | "$python_bin" -c 'import json,sys; assert len(json.load(sys.stdin)) == 1'
backup_file="$(C2CDIRECT_BACKUP_DIR="$backup_dir" C2CDIRECT_ENV_FILE="$smoke_env" C2CDIRECT_COMPOSE_PROJECT="$project" "$repo_dir/deploy/core/backup.sh")"
C2CDIRECT_ENV_FILE="$smoke_env" C2CDIRECT_COMPOSE_PROJECT="$project" "$repo_dir/deploy/core/restore-verify.sh" "$backup_file" >/dev/null
echo "C2CDirect Core smoke test passed."
