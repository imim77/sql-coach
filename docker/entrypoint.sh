#!/bin/bash
# One container: Northline Postgres, then the API and the built page.
set -euo pipefail

if [[ $# -gt 0 ]]; then
  exec "$@"
fi

export POSTGRES_USER="${POSTGRES_USER:-sqlcoach}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-sqlcoach}"
export POSTGRES_DB="${POSTGRES_DB:-sqlcoach}"
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export PGPASSWORD="$POSTGRES_PASSWORD"

pg_pid=""
app_pid=""
stopping=0

shutdown() {
  local status="${1:-0}"
  if [[ "$stopping" -eq 1 ]]; then
    return
  fi
  stopping=1
  if [[ -n "$app_pid" ]] && kill -0 "$app_pid" 2>/dev/null; then
    kill -TERM "$app_pid" 2>/dev/null || true
  fi
  if [[ -n "$pg_pid" ]] && kill -0 "$pg_pid" 2>/dev/null; then
    kill -TERM "$pg_pid" 2>/dev/null || true
  fi
  wait || true
  exit "$status"
}

trap 'shutdown 0' INT TERM

docker-entrypoint.sh postgres &
pg_pid=$!

ready_flag="${PGDATA}/.sqlcoach-ready"
for _ in $(seq 1 180); do
  if [[ -f "$ready_flag" ]]; then
    break
  fi
  if ! kill -0 "$pg_pid" 2>/dev/null; then
    wait "$pg_pid"
    exit $?
  fi
  sleep 0.5
done

if [[ ! -f "$ready_flag" ]]; then
  echo "Practice database did not finish initializing." >&2
  shutdown 1
fi

ready_epoch="$(stat -c %Y "$ready_flag")"
stable=""
ready=0
for _ in $(seq 1 180); do
  if ! kill -0 "$pg_pid" 2>/dev/null; then
    wait "$pg_pid"
    exit $?
  fi
  if pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    start_epoch="$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
      "SELECT floor(extract(epoch from pg_postmaster_start_time()))::bigint" 2>/dev/null || true)"
    if [[ -n "$start_epoch" && "$start_epoch" -ge "$ready_epoch" ]]; then
      if [[ "$start_epoch" == "$stable" ]]; then
        ready=1
        break
      fi
      stable="$start_epoch"
      sleep 1
      continue
    fi
  fi
  stable=""
  sleep 0.5
done

if [[ "$ready" -ne 1 ]]; then
  echo "Practice database did not become ready." >&2
  shutdown 1
fi

cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
app_pid=$!

status=0
wait -n "$pg_pid" "$app_pid" || status=$?
shutdown "$status"
