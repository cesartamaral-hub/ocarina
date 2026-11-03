#!/bin/bash
# Development mode: backend from source + Vite with hot reload.
#
#   ./dev.sh            use a COPY of your library (made on first run; safe to experiment)
#   ./dev.sh --fresh    throw the copy away and make a new one from your real library
#   ./dev.sh --real     use your REAL library (audio jobs can replace your recordings)
#
# Open http://localhost:5173/ocarina/app/  -- Ctrl-C stops both servers.
set -e
cd "$(dirname "$0")/.."
REAL="$HOME/Library/Application Support/Ocarina"
COPY="$HOME/Lute-Ocarina/dev-data"

if [ "$1" = "--real" ]; then
  DATA="$REAL"
else
  DATA="$COPY"
  [ "$1" = "--fresh" ] && rm -rf "$COPY"
  if [ ! -d "$COPY" ]; then
    echo "Copying your library to $COPY ..."
    mkdir -p "$COPY"
    sqlite3 -readonly "$REAL/ocarina.db" ".backup '$COPY/ocarina.db'"
    cp -R "$REAL/useraudio" "$REAL/userimages" "$COPY/" 2>/dev/null || true
  fi
fi

.venv/bin/python desktop/dev_server.py "$DATA" 5001 &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
