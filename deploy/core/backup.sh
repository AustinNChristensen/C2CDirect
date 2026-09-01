#!/usr/bin/env bash
set -euo pipefail

deployment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="${C2CDIRECT_ENV_FILE:-$deployment_dir/.env}"
compose_project="${C2CDIRECT_COMPOSE_PROJECT:-c2cdirect-core}"
backup_dir="${C2CDIRECT_BACKUP_DIR:-$deployment_dir/backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$backup_dir/c2cdirect-$timestamp.dump"
temporary="$destination.part"

mkdir -p "$backup_dir"
umask 077
docker compose -p "$compose_project" --env-file "$env_file" -f "$deployment_dir/compose.yml" \
  exec -T postgres pg_dump -U c2cdirect -d c2cdirect -Fc > "$temporary"
docker compose -p "$compose_project" --env-file "$env_file" -f "$deployment_dir/compose.yml" \
  exec -T postgres pg_restore --list < "$temporary" >/dev/null
mv "$temporary" "$destination"
echo "$destination"
