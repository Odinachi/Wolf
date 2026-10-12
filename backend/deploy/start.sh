#!/bin/sh
# Starts the API. When LITESTREAM_BUCKET is set, the SQLite database is restored from the bucket on
# first boot (e.g. a fresh volume) and continuously replicated to it while the API runs.
set -e

export WOLF_DATA_DIR="${WOLF_DATA_DIR:-/data}"
mkdir -p "$WOLF_DATA_DIR"
DB="$WOLF_DATA_DIR/wolf.db"
# One worker: the "AI is already running" guard lives in memory, and SQLite has a single writer.
APP="uvicorn wolf_api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"

if [ -z "$LITESTREAM_BUCKET" ]; then
  exec $APP
fi

# Litestream talks to Google Cloud Storage (Firebase Storage buckets are GCS buckets) using the
# same service account as the app.
if [ -n "$FIREBASE_SERVICE_ACCOUNT" ] && [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  creds=/tmp/gcp-credentials.json
  case "$FIREBASE_SERVICE_ACCOUNT" in
    \{*) printf '%s' "$FIREBASE_SERVICE_ACCOUNT" > "$creds" ;;
    *) printf '%s' "$FIREBASE_SERVICE_ACCOUNT" | base64 -d > "$creds" ;;
  esac
  chmod 600 "$creds"
  export GOOGLE_APPLICATION_CREDENTIALS="$creds"
fi

litestream restore -config /app/litestream.yml -if-db-not-exists -if-replica-exists "$DB"
exec litestream replicate -config /app/litestream.yml -exec "$APP"
