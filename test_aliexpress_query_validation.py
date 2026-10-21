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
METHOD = "aliexpress.affiliate.product.query"
SDK_PARTNER = "iop44-sdk-typescript-20231021"
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


def call(keyword: str, currency: str, language: str, country: str, fields: str) -> None:
    token_data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    access_token = token_data["access_token"]

    params = {
        "app_key": str(ALI_APP_KEY),
        "session": str(access_token),
        "format": "json",
        "method": METHOD,
        "partner_id": SDK_PARTNER,
        "sign_method": "sha256",
        "simplify": "false",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0",
        "keywords": keyword,
        "page_no": "1",
        "page_size": "5",
        "fields": fields,
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": currency,
        "target_language": language,
        "ship_to_country": country,
    }

    params["sign"] = sign(params)

    print(f"\n--- Consulta: {keyword!r} / {currency} / {country} ---")
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
        print("Respuesta no JSON:", r.text[:1500])
        return

    if "error_response" in data:
        err = data["error_response"]
        print("Error response:", err)
        return

    root = data.get("aliexpress_affiliate_product_query_response", {})
    rr = root.get("resp_result", {}) if isinstance(root, dict) else {}
    print("resp_code:", rr.get("resp_code"))
    print("resp_msg:", rr.get("resp_msg"))

    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products_obj = result.get("products", {}) if isinstance(result, dict) else {}
    products = products_obj.get("product", []) if isinstance(products_obj, dict) else []

    if not isinstance(products, list) or not products:
        print("Productos recibidos: 0")
        return

    print("Productos recibidos:", len(products))
    for i, p in enumerate(products[:5], 1):
        if not isinstance(p, dict):
            continue
        title = p.get("product_title", "<sin título>")
        price = p.get("app_sale_price") or p.get("target_sale_price") or p.get("sale_price")
        original = p.get("original_price")
        discount = p.get("discount")
        pid = p.get("product_id")
        link = p.get("promotion_link")
        image = p.get("product_main_image_url")
        print(f"{i}. {title}")
        print(f"   id={pid} | precio={price} | original={original} | descuento={discount}")
        print(f"   affiliate_url={'OK' if link else 'NO'} | image={'OK' if image else 'NO'}")


def main() -> int:
    if not TOKEN_FILE.exists():
        print("ERROR: falta data/aliexpress_token.json")
        return 2

    # First: exact style of the current official documentation example.
    call("mp3", "USD", "EN", "US", "commission_rate,sale_price")

    # Second: tech query for the user's actual market.
    call("bluetooth earphones", "EUR", "ES", "ES", "commission_rate,sale_price")

    print("\nFIN: prueba de disponibilidad de catálogo.")
    print("No modifica SQLite, scanner ni Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
