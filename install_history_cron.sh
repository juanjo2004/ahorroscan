#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/debian/ahorroscan/test/current/telegram-bot-v2"
RUNNER="$BASE_DIR/run_history_scan.sh"
MARKER="# TELEGRAM-BOT-V2-HISTORY"
CRON_LINE="15 3 * * * $RUNNER >> $BASE_DIR/logs/cron.log 2>&1 $MARKER"

mkdir -p "$BASE_DIR/logs"

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$MARKER" > "$TMP_FILE" || true
echo "$CRON_LINE" >> "$TMP_FILE"
crontab "$TMP_FILE"
rm -f "$TMP_FILE"

echo "OK: cron instalado."
echo "Horario: todos los días a las 03:15 (hora local de la Raspberry)."
echo "Comando: $RUNNER"
echo "Log: $BASE_DIR/logs/history_collector.log"
echo
crontab -l | grep "$MARKER"
