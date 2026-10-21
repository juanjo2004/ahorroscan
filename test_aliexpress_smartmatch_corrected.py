#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path

import requests

from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID

ENDPOINT = "https://api-sg.aliexpress.com/sync"
METHOD = "aliexpress.affiliate.product.smartmatch"
PARTNER_ID = "iop44-sdk-typescript-20231021"
TOKEN_FILE = Path("data/aliexpress_token.json")


def sign(params: dict[str, str]) -> str:
    canonical = "".join(
        key + str(value)
        for key, value in sorted(params.items())
        if value is not None and str(value) != ""
    )
    return hmac.new(
        str(ALI_APP_SECRET).encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


def run_query(keyword: str) -> None:
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("Falta access_token en data/aliexpress_token.json")

    # IMPORTANT: SmartMatch documents device_id as required. The previous
    # probe omitted it, so this probe uses a synthetic stable device id.
    params = {
        "app_key": str(ALI_APP_KEY),
        "session": str(access_token),
        "format": "json",
        "method": METHOD,
        "partner_id": PARTNER_ID,
        "sign_method": "sha256",
        "simplify": "false",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0",
        "device_id": "telegramdeals-raspi4",
        "keywords": keyword,
        "page_no": "1",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "country": "ES",
        "fields": "app_sale_price,commission_rate,discount,first_level_category_name,second_level_category_name,lastest_volume,original_price,product_detail_url,product_id,product_main_image_url,product_title",
    }
    params["sign"] = sign(params)

    print(f"\n=== {keyword} ===")
    try:
        r = requests.post(
            ENDPOINT,
            data=params,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
    except requests.RequestException as exc:
        print("ERROR conexión:", type(exc).__name__, exc)
        return

    print("HTTP:", r.status_code)
    try:
        data = r.json()
    except ValueError:
        print("Respuesta no JSON:", r.text[:1600])
        return

    root = data.get("aliexpress_affiliate_product_smartmatch_response")
    if not isinstance(root, dict):
        print("Estructura inesperada:", repr(data)[:2400])
        return

    rr = root.get("resp_result", {})
    if not isinstance(rr, dict):
        print("resp_result inesperado:", repr(root)[:2000])
        return

    print("resp_code:", rr.get("resp_code"))
    print("resp_msg:", rr.get("resp_msg"))

    result = rr.get("result", {})
    if not isinstance(result, dict):
        print("Sin result.")
        return

    products_obj = result.get("products", {})
    if not isinstance(products_obj, dict):
        print("Sin products.")
        print("Result resumido:", repr(result)[:2000])
        return

    products = products_obj.get("product", [])
    if not isinstance(products, list):
        products = []

    print("Productos:", len(products))
    for i, p in enumerate(products[:5], 1):
        if not isinstance(p, dict):
            continue
        print(f"{i}. {p.get('product_title', '<sin título>')}")
        print(
            f"   precio={p.get('app_sale_price', 'n/d')} | "
            f"original={p.get('original_price', 'n/d')} | "
            f"descuento={p.get('discount', 'n/d')}"
        )
        print(
            f"   rating={p.get('evaluate_rate', 'n/d')} | "
            f"ventas={p.get('lastest_volume', 'n/d')} | "
            f"cat1={p.get('first_level_category_name', 'n/d')} | "
            f"cat2={p.get('second_level_category_name', 'n/d')}"
        )
        print(
            f"   id={p.get('product_id', 'n/d')} | "
            f"affiliate={'OK' if p.get('promotion_link') else 'NO'} | "
            f"image={'OK' if p.get('product_main_image_url') else 'NO'}"
        )


def main() -> int:
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("ERROR: faltan credenciales de AliExpress en .env")
        return 2
    if not TOKEN_FILE.exists():
        print("ERROR: falta data/aliexpress_token.json")
        return 3

    print("ALIEXPRESS SMARTMATCH - PRUEBA CORREGIDA")
    print("Cambio clave respecto al probe anterior: device_id incluido (obligatorio).")
    print("No modifica SQLite, scanner ni Telegram.")
    run_query("raton gaming")
    run_query("ssd nvme")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
