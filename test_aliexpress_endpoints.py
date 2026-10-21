#!/usr/bin/env python3
"""Diagnóstico aislado de endpoints TOP/AliExpress.

Hace una sola consulta por endpoint y nunca imprime app_secret ni la firma.
No modifica el scanner ni la base de datos.
"""
from __future__ import annotations

import hashlib
import hmac
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# Carga .env mediante el config.py del proyecto V2
try:
    from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID
except Exception as exc:
    print(f"ERROR: no se pudo cargar config.py: {exc}")
    sys.exit(1)

QUERY = "nvme 1tb"
METHOD = "aliexpress.affiliate.product.query"
TIMEOUT = 20

# La documentación oficial muestra eco.taobao.com como HTTPS de producción.
# Incluimos también las variantes de gateway para diagnóstico, sin tocar el código del bot.
ENDPOINTS = [
    "https://eco.taobao.com/router/rest",
    "https://gw.api.taobao.com/router/rest",
    "https://api.taobao.com/router/rest",
]


def top_sign(params: dict[str, str], secret: str) -> str:
    """Firma TOP: HMAC-MD5 sobre METHOD + claves/valores ordenados."""
    canonical = METHOD + "".join(f"{k}{params[k]}" for k in sorted(params))
    digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.md5)
    return digest.hexdigest().upper()


def build_params() -> dict[str, str]:
    # Timestamp requerido por TOP: yyyy-MM-dd HH:mm:ss en GMT+8.
    gmt8 = timezone(timedelta(hours=8))
    timestamp = datetime.now(gmt8).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "app_key": str(ALI_APP_KEY).strip(),
        "format": "json",
        "method": METHOD,
        "sign_method": "hmac",
        "timestamp": timestamp,
        "v": "2.0",
        "simplify": "true",
        "keywords": QUERY,
        "page_no": "1",
        "page_size": "5",
        "tracking_id": str(ALI_TRACKING_ID).strip(),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
        "fields": "product_id,product_title,app_sale_price,original_price,sale_price,discount,product_main_image_url,product_detail_url,promotion_link,commission_rate",
    }


def classify(body: str) -> str:
    low = body.lower()
    if "invalid app key" in low or "api 29" in low:
        return "API 29: Invalid app Key"
    if "invalid signature" in low or "incompletesignature" in low or "signature" in low:
        return "firma/autenticación rechazada"
    if "error_response" in low:
        return "error_response (ver detalle abajo)"
    return "respuesta no clasificada"


def main() -> int:
    app_key = str(ALI_APP_KEY).strip()
    app_secret = str(ALI_APP_SECRET).strip()
    tracking = str(ALI_TRACKING_ID).strip()

    if not app_key or not app_secret or not tracking:
        print("ERROR: faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")
        return 2

    print(f"Diagnóstico AliExpress para: '{QUERY}'")
    print(f"App Key presente: SÍ (longitud {len(app_key)})")
    print(f"Tracking ID presente: {'SÍ' if tracking else 'NO'}")
    print("No se muestran secretos ni firmas.")

    for endpoint in ENDPOINTS:
        params = build_params()
        params["sign"] = top_sign(params, app_secret)
        print(f"\n--- {endpoint} ---")
        try:
            response = requests.post(
                endpoint,
                data=params,
                timeout=TIMEOUT,
                headers={"User-Agent": "telegram-bot-v2-aliexpress-diagnostic/1.0"},
            )
            body = response.text or ""
            print(f"HTTP: {response.status_code}")
            print(f"Resultado: {classify(body)}")

            # Intentamos extraer una respuesta útil sin volcar secretos ni todo el payload.
            text = body.replace("\n", " ")
            lower = text.lower()
            keys = [
                "error_code",
                "sub_code",
                "msg",
                "sub_msg",
                "total_record_count",
                "product_count",
            ]
            found = []
            for key in keys:
                pos = lower.find(key)
                if pos >= 0:
                    snippet = text[max(0, pos - 20): min(len(text), pos + 160)]
                    found.append(f"{key}: {snippet}")
            if found:
                for item in found[:6]:
                    print(item)
            else:
                print(f"Respuesta (primeros 300 chars): {text[:300]}")
        except requests.RequestException as exc:
            print(f"ERROR de conexión: {exc.__class__.__name__}: {exc}")
        except Exception as exc:
            print(f"ERROR inesperado: {exc.__class__.__name__}: {exc}")

    print("\nFIN diagnóstico. No se ha modificado SQLite, scanner ni Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
