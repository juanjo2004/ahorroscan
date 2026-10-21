#!/bin/bash
set -u
ROOT="/home/debian/ahorroscan/production/current/telegram-bot-v2"
LOG="$ROOT/logs/prime_day_tech_loop.log"
CUTOFF="2026-10-08T00:00:00+00:00"
echo "$(date -Is) PRIME_DAY_LOOP inicio; frecuencia objetivo=30m; fin=$CUTOFF" >> "$LOG"
while [ "$(date -u +%s)" -lt "$(date -d "$CUTOFF" +%s)" ]; do
  echo "$(date -Is) PRIME_DAY_LOOP ciclo" >> "$LOG"
  cd "$ROOT" || exit 1
  PRIME_DAY_MODE=1 PRIME_DAY_BROAD_MODE=1 PRIME_DAY_ALLOW_NON_AMAZON_FALLBACK=1 PRIME_DAY_FALLBACK_MIN_DISCOUNT=15 TECH_IGNORE_HISTORY=1 MAX_PUBLICATIONS_PER_DAY=120 bash ./run_auto.sh >> "$LOG" 2>&1 || true
  [ "$(date -u +%s)" -ge "$(date -d "$CUTOFF" +%s)" ] && break
  sleep 1800
done
echo "$(date -Is) PRIME_DAY_LOOP fin" >> "$LOG"
