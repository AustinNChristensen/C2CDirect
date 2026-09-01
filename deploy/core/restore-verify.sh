#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Usage: deploy/core/restore-verify.sh /path/to/c2cdirect-backup.dump"
  exit 1
fi

deployment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="${C2CDIRECT_ENV_FILE:-$deployment_dir/.env}"
compose_project="${C2CDIRECT_COMPOSE_PROJECT:-c2cdirect-core}"
dump_file="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
temporary_database="c2cdirect_restore_$(date -u +%Y%m%d%H%M%S)"

cleanup() {
  docker compose -p "$compose_project" --env-file "$env_file" -f "$deployment_dir/compose.yml" \
    exec -T postgres dropdb -U c2cdirect --if-exists "$temporary_database" >/dev/null
}
trap cleanup EXIT

docker compose -p "$compose_project" --env-file "$env_file" -f "$deployment_dir/compose.yml" \
  exec -T postgres createdb -U c2cdirect "$temporary_database"
docker compose -p "$compose_project" --env-file "$env_file" -f "$deployment_dir/compose.yml" \
  exec -T postgres pg_restore -U c2cdirect -d "$temporary_database" \
    --no-owner --no-privileges < "$dump_file"
docker compose -p "$compose_project" --env-file "$env_file" -f "$deployment_dir/compose.yml" \
  exec -T postgres psql -U c2cdirect -d "$temporary_database" \
    -v ON_ERROR_STOP=1 -c "SELECT count(*) AS jobs FROM jobs; SELECT count(*) AS profiles FROM search_profiles;"
echo "Restore verified in an isolated temporary database. The live database was not changed."
