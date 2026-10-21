#!/usr/bin/env bash
set -euo pipefail

BASE="/home/debian/ahorroscan/test/current/telegram-bot-v2"
ENV_FILE="$BASE/.env"
API_VERSION="${INSTAGRAM_API_VERSION:-v26.0}"

cd "$BASE"

read -rsp "Pega el token de Instagram y pulsa Enter: " TOKEN
echo

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: token vacío."
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

grep -v '^INSTAGRAM_' "$ENV_FILE" 2>/dev/null > "$TMP" || true
cat >> "$TMP" <<EOF
INSTAGRAM_ACCESS_TOKEN=$TOKEN
INSTAGRAM_API_VERSION=$API_VERSION
EOF

install -m 600 "$TMP" "$ENV_FILE"

echo "Token guardado en .env con permisos 600."
echo "Comprobando acceso de Instagram..."

RESP="$(curl -sS --get "https://graph.instagram.com/$API_VERSION/me" \
  --data-urlencode "fields=id,user_id,username" \
  --data-urlencode "access_token=$TOKEN")"

if echo "$RESP" | grep -q '"id"'; then
  echo "OK: acceso válido."
  echo "$RESP" | sed -E 's/"(access_token|accessToken)"[[:space:]]*:[[:space:]]*"[^"]+"/"\1":"<redacted>"/g'
else
  echo "ERROR: Instagram no ha validado el token."
  echo "$RESP"
  exit 2
fi
