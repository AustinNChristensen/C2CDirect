#!/bin/sh
set -eu
umask 077

deployment_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
backup_dir="${C2CDIRECT_BACKUP_DIR:-$deployment_dir/backups}"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$backup_dir"
destination="$backup_dir/c2cdirect-$timestamp.dump"
temporary="$destination.partial"
trap 'rm -f "$temporary"' EXIT HUP INT TERM

docker compose --env-file "$deployment_dir/.env" -f "$deployment_dir/compose.yml" \
  exec -T postgres pg_dump -U c2cdirect -d c2cdirect -Fc \
  > "$temporary"

docker compose --env-file "$deployment_dir/.env" -f "$deployment_dir/compose.yml" \
  exec -T postgres pg_restore --list < "$temporary" >/dev/null
mv "$temporary" "$destination"
trap - EXIT HUP INT TERM

find "$backup_dir" -type f -name 'c2cdirect-*.dump' -mtime +14 -delete
echo "Backup written to $destination"
