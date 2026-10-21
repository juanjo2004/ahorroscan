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
PARTNER_ID = "iop44-sdk-typescript-20231021"
TOKEN_FILE = Path("data/aliexpress_token.json")

QUERIES = [
    "raton gaming",
    "ssd nvme",
    "memoria ram ddr5",
    "ryzen 7",
    "monitor 4k",
    "router wifi 6",
    "cargador usb c",
    "webcam 1080p",
    "teclado mecanico",
    "auriculares bluetooth",
]


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


def query(keyword: str) -> list[dict]:
    token_data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("data/aliexpress_token.json no contiene access_token")

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
        "keywords": keyword,
        "page_no": "1",
        "page_size": "5",
        "fields": "commission_rate,sale_price",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
    }
    params["sign"] = sign(params)

    response = requests.post(
        ENDPOINT,
        data=params,
        timeout=30,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    response.raise_for_status()
    data = response.json()

    root = data.get("aliexpress_affiliate_product_query_response", {})
    rr = root.get("resp_result", {}) if isinstance(root, dict) else {}
    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products_obj = result.get("products", {}) if isinstance(result, dict) else {}
    products = products_obj.get("product", []) if isinstance(products_obj, dict) else []

    if not isinstance(products, list):
        return []

    return [p for p in products if isinstance(p, dict)]


def money(p: dict, *keys: str) -> str:
    for k in keys:
        if p.get(k) not in (None, ""):
            return str(p[k])
    return "n/d"


def main() -> int:
    print("ALIEXPRESS CATÁLOGO TECNOLÓGICO - PROBE")
    print("Consulta 10 búsquedas representativas. No escribe SQLite ni Telegram.")
    print()

    for keyword in QUERIES:
        print(f"=== {keyword} ===")
        try:
            products = query(keyword)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            print()
            continue

        print(f"Resultados: {len(products)}")
        for i, p in enumerate(products[:5], 1):
            print(f"{i}. {p.get('product_title', '<sin título>')}")
            print(
                "   "
                f"precio={money(p, 'target_sale_price', 'sale_price')} | "
                f"original={money(p, 'target_original_price', 'original_price')} | "
                f"descuento={p.get('discount', 'n/d')} | "
                f"evaluate_rate={p.get('evaluate_rate', 'n/d')} | "
                f"volumen={p.get('lastest_volume', 'n/d')}"
            )
            print(
                "   "
                f"id={p.get('product_id', 'n/d')} | "
                f"affiliate={'OK' if p.get('promotion_link') else 'NO'} | "
                f"image={'OK' if p.get('product_main_image_url') else 'NO'}"
            )
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
