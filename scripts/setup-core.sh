#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
deploy_dir="$repo_dir/deploy/core"
env_file="$deploy_dir/.env"
core_port="8080"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop or Docker Engine, then run this again."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for the Core health check. Install curl, then run this again."
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL is required to generate private Core credentials. Install OpenSSL, then run this again."
  exit 1
fi

if [[ -e "$env_file" ]]; then
  echo "Updating C2CDirect Core with the saved private configuration…"
  docker compose --env-file "$env_file" -f "$deploy_dir/compose.yml" up -d --build
  saved_port="$(sed -n 's/^CORE_PORT=//p' "$env_file" | tail -1)"
  base_url="http://127.0.0.1:${saved_port:-8080}"

  echo "Waiting for C2CDirect Core to become healthy…"
  healthy=false
  for ((attempt = 1; attempt <= 120; attempt++)); do
    if curl -fsSL "$base_url/api/health" >/dev/null 2>&1 && \
       curl -fsSL "$base_url/" >/dev/null 2>&1; then
      healthy=true
      break
    fi
    sleep 1
  done

  if [[ "$healthy" != "true" ]]; then
    echo "Error: C2CDirect Core did not become healthy within 120 seconds."
    echo "Service status:"
    docker compose --env-file "$env_file" -f "$deploy_dir/compose.yml" ps
    echo ""
    echo "Recent logs from web service:"
    docker compose --env-file "$env_file" -f "$deploy_dir/compose.yml" logs --tail=50 web
    echo ""
    echo "Run 'docker compose --env-file deploy/core/.env -f deploy/core/compose.yml logs' for full logs."
    exit 1
  fi

  echo "C2CDirect Core is ready at $base_url"
  echo "Open Setup to connect your AI brain and import your first jobs."
  echo "Import the demo jobs from examples/demo-jobs.json to get started quickly."
  exit 0
fi

echo "C2CDirect Core setup"
echo "Press Enter for deterministic local screening with no model cost."

if [[ "${C2CDIRECT_NONINTERACTIVE:-false}" == "true" ]]; then
  model_url="${C2CDIRECT_MODEL_BASE_URL:-}"
  model_name="${C2CDIRECT_MODEL_NAME:-local-rules}"
  model_key="${C2CDIRECT_MODEL_API_KEY:-}"
  input_cost="${C2CDIRECT_MODEL_INPUT_COST_PER_MILLION:-0}"
  output_cost="${C2CDIRECT_MODEL_OUTPUT_COST_PER_MILLION:-0}"
  web_search_choice="${C2CDIRECT_WEB_SEARCH:-Y}"
  echo "Running in non-interactive mode (C2CDIRECT_NONINTERACTIVE=true)"
else
  read -r -p "OpenAI-compatible base URL (example: http://host.docker.internal:11434/v1): " model_url
fi

model_provider="deterministic"
model_name="${model_name:-local-rules}"
model_key="${model_key:-}"
input_cost="${input_cost:-0}"
output_cost="${output_cost:-0}"

if [[ -n "$model_url" ]]; then
  model_provider="openai_compatible"
  if [[ "${C2CDIRECT_NONINTERACTIVE:-false}" != "true" ]]; then
    read -r -p "Model name: " model_name
  fi
  if [[ -z "$model_name" ]]; then
    echo "A model name is required when a model URL is configured."
    exit 1
  fi
  if [[ "${C2CDIRECT_NONINTERACTIVE:-false}" != "true" ]]; then
    read -r -s -p "API key (optional; input hidden): " model_key
    echo
    read -r -p "Input cost per 1M tokens [0]: " input_cost
    read -r -p "Output cost per 1M tokens [0]: " output_cost
  fi
  input_cost="${input_cost:-0}"
  output_cost="${output_cost:-0}"
fi

if [[ "${C2CDIRECT_NONINTERACTIVE:-false}" != "true" ]]; then
  read -r -p "Include private Web Scout search (SearXNG)? [Y/n]: " web_search_choice
fi
compose_profiles="web-search"
if [[ "${web_search_choice:-Y}" =~ ^[Nn]$ ]]; then
  compose_profiles=""
fi

umask 077
postgres_password="$(openssl rand -hex 32)"
app_database_password="$(openssl rand -hex 32)"
config_encryption_key="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')"
searxng_secret="$(openssl rand -hex 32)"

{
  echo "POSTGRES_PASSWORD=$postgres_password"
  echo "APP_DATABASE_PASSWORD=$app_database_password"
  echo "AUTH_DISABLED_FOR_LOCAL_DEV=true"
  echo "C2CDIRECT_CONFIG_ENCRYPTION_KEY=$config_encryption_key"
  echo "EMAIL_TOKEN_ENCRYPTION_KEY=$config_encryption_key"
  echo "SEARXNG_SECRET=$searxng_secret"
  echo "COMPOSE_PROFILES=$compose_profiles"
  echo "CORE_PORT=$core_port"
  echo "SOURCE_URL=https://directc2c.com/#core"
  echo "C2CDIRECT_MODEL_PROVIDER=$model_provider"
  echo "C2CDIRECT_MODEL_BASE_URL=$model_url"
  echo "C2CDIRECT_MODEL_NAME=$model_name"
  echo "C2CDIRECT_MODEL_API_KEY=$model_key"
  echo "C2CDIRECT_MODEL_INPUT_COST_PER_MILLION=$input_cost"
  echo "C2CDIRECT_MODEL_OUTPUT_COST_PER_MILLION=$output_cost"
  echo "C2CDIRECT_MODEL_TIMEOUT_SECONDS=30"
  echo "DAILY_AI_BUDGET_USD=10"
  echo "MAX_RUN_COST_USD=0.10"
  echo "MAX_RUN_TOKENS=12000"
} > "$env_file"

echo "Starting C2CDirect Core…"
docker compose --env-file "$env_file" -f "$deploy_dir/compose.yml" up -d --build

base_url="http://127.0.0.1:$core_port"
echo "Waiting for C2CDirect Core to become healthy…"
healthy=false
for ((attempt = 1; attempt <= 120; attempt++)); do
  if curl -fsSL "$base_url/api/health" >/dev/null 2>&1 && \
     curl -fsSL "$base_url/" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done

if [[ "$healthy" != "true" ]]; then
  echo "Error: C2CDirect Core did not become healthy within 120 seconds."
  echo "Service status:"
  docker compose --env-file "$env_file" -f "$deploy_dir/compose.yml" ps
  echo ""
  echo "Recent logs from web service:"
  docker compose --env-file "$env_file" -f "$deploy_dir/compose.yml" logs --tail=50 web
  echo ""
  echo "Run 'docker compose --env-file deploy/core/.env -f deploy/core/compose.yml logs' for full logs."
  exit 1
fi

echo "C2CDirect Core is ready at $base_url"
echo "Open Setup to connect your AI brain and import your first jobs."
echo "Import the demo jobs from examples/demo-jobs.json to get started quickly."
