#!/bin/bash
set -euo pipefail

ROOT="/home/debian/ahorroscan/test/current/telegram-bot-v2"
LOG="$ROOT/logs/mobile_runner.log"
LOCK="$ROOT/data/mobile_runner.lock"

mkdir -p "$ROOT/logs" "$ROOT/data"

exec 9>"$LOCK"
flock -n 9 || exit 0

cd "$ROOT"
source "$ROOT/venv/bin/activate"

{
    echo "=== MOBILE RUN $(date -Is) ==="
    python "$ROOT/run_mobile.py"
    echo "=== MOBILE RUN END $(date -Is) ==="
} >> "$LOG" 2>&1