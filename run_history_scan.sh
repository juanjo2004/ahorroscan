#!/usr/bin/env bash
set -u

BASE_DIR="/home/debian/ahorroscan/test/current/telegram-bot-v2"
VENV_PYTHON="$BASE_DIR/venv/bin/python"
LOCK_FILE="$BASE_DIR/.history_scan.lock"
HC="/home/debian/ahorroscan/test/current/superofertastech-web/monitor/healthcheck_ping.sh"

cd "$BASE_DIR" || exit 1
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "ERROR: no existe el Python del venv: $VENV_PYTHON" >&2
  "$HC" TECH_HISTORY fail
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Scan histórico ya en ejecución. Se omite esta ejecución."
  exit 0
fi

"$HC" TECH_HISTORY start
"$VENV_PYTHON" "$BASE_DIR/history_collector.py"
STATUS=$?

[ "$STATUS" -eq 0 ] && "$HC" TECH_HISTORY success || "$HC" TECH_HISTORY fail
exit "$STATUS"
