#!/bin/sh
set -eu

if [ -z "${APP_DATABASE_PASSWORD:-}" ]; then
  echo "APP_DATABASE_PASSWORD is required" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$APP_DATABASE_PASSWORD" <<'SQL'
ALTER ROLE c2cdirect_app LOGIN PASSWORD :'app_password';
SQL
