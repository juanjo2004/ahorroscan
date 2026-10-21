#!/usr/bin/env bash
set -euo pipefail
MARKER="# TELEGRAM-BOT-V2-HISTORY"
TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$MARKER" > "$TMP_FILE" || true
crontab "$TMP_FILE"
rm -f "$TMP_FILE"
echo "OK: cron de histórico eliminado."
