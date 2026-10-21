#!/bin/bash
set -u
ROOT="/home/debian/ahorroscan/production/current/telegram-bot-v2"
LOG="$ROOT/logs/prime_day_multichannel_loop.log"
CUTOFF="2026-10-08T00:00:00+00:00"
CHANNELS=(moviles mascotas hogar moda deportes)
echo "$(date -Is) PRIME_DAY_MULTICHANNEL inicio; frecuencia objetivo=60m; fin=$CUTOFF" >> "$LOG"
while [ "$(date -u +%s)" -lt "$(date -d "$CUTOFF" +%s)" ]; do
  echo "$(date -Is) PRIME_DAY_MULTICHANNEL ciclo" >> "$LOG"
  cd "$ROOT" || exit 1
  for channel in "${CHANNELS[@]}"; do
    echo "$(date -Is) PRIME_DAY_MULTICHANNEL canal=$channel" >> "$LOG"
    PRIME_DAY_MODE=1 PRIME_DAY_BROAD_MODE=1 "$ROOT/venv/bin/python" "$ROOT/run_multichannel.py" --publish --channel "$channel" >> "$LOG" 2>&1 || true
  done
  [ "$(date -u +%s)" -ge "$(date -d "$CUTOFF" +%s)" ] && break
  sleep 3600
done
echo "$(date -Is) PRIME_DAY_MULTICHANNEL fin" >> "$LOG"
