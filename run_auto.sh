#!/bin/bash
set -u

BASE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="$BASE_DIR/data/auto_runner.lock"
LOG_FILE="$BASE_DIR/logs/auto_runner.log"
PROJECT_ROOT="$(dirname "$BASE_DIR")"
HC="$PROJECT_ROOT/superofertastech-web/monitor/healthcheck_ping.sh"

# Límites diarios y por ejecución alineados con la configuración de Tech.
export MAX_PUBLICATIONS_PER_RUN="${MAX_PUBLICATIONS_PER_RUN:-12}"
# Prime Day terminó: volver al filtro normal y al histórico de precios.
export PRIME_DAY_BROAD_MODE="${PRIME_DAY_BROAD_MODE:-0}"
export MAX_PUBLICATIONS_PER_DAY="${MAX_PUBLICATIONS_PER_DAY:-60}"
export SCAN_MODE="${SCAN_MODE:-discovery}"
export TECH_IGNORE_HISTORY="${TECH_IGNORE_HISTORY:-0}"

cd "$BASE_DIR" || exit 1
mkdir -p "$BASE_DIR/data" "$BASE_DIR/logs"
PYTHON_BIN="${AHOROSCAN_TECH_PYTHON:-$BASE_DIR/venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="${AHOROSCAN_TECH_PYTHON:-$BASE_DIR/.venv/bin/python}"
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "No se encontró el intérprete Python de Tech." >&2
    exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "$(date -Is) [AUTO] Otra ejecución ya está en marcha. Se omite." >> "$LOG_FILE"
    exit 0
fi

"$HC" TECH_AUTO start
echo "" >> "$LOG_FILE"
echo "============================================================" >> "$LOG_FILE"
echo "$(date -Is) [AUTO] INICIO" >> "$LOG_FILE"

"$PYTHON_BIN" -u "$BASE_DIR/auto_runner.py" >> "$LOG_FILE" 2>&1
STATUS=$?

echo "$(date -Is) [AUTO] FIN status=$STATUS" >> "$LOG_FILE"
[ "$STATUS" -eq 0 ] && "$HC" TECH_AUTO success || "$HC" TECH_AUTO fail

exit "$STATUS"
