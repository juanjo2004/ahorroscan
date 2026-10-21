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

QUERIES = [
    "raton gaming",
    "ssd nvme",
    "memoria ram ddr5",
    "ryzen 7",
    "monitor 4k",
    "teclado mecanico",
    "webcam 1080p",
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


def query(keyword: str) -> tuple[int | None, str | None, list[dict]]:
    params = {
        "app_key": str(ALI_APP_KEY),
        "format": "json",
        "method": METHOD,
        "partner_id": PARTNER_ID,
        "sign_method": "sha256",
        "simplify": "false",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0",
        "keywords": keyword,
        "page_no": "1",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "country": "ES",
        "fields": "app_sale_price,target_app_sale_price,original_price,discount,product_title,product_id,product_main_image_url,product_detail_url,promotion_link,first_level_category_name,second_level_category_name,lastest_volume,evaluate_rate,commission_rate",
    }

    params["sign"] = sign(params)

    r = requests.post(
        ENDPOINT,
        data=params,
        timeout=30,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    r.raise_for_status()
    data = r.json()

    root = data.get("aliexpress_affiliate_product_smartmatch_response", {})
    rr = root.get("resp_result", {}) if isinstance(root, dict) else {}

    code = rr.get("resp_code") if isinstance(rr, dict) else None
    msg = rr.get("resp_msg") if isinstance(rr, dict) else None

    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products_obj = result.get("products", {}) if isinstance(result, dict) else {}
    products = products_obj.get("product", []) if isinstance(products_obj, dict) else []

    if not isinstance(products, list):
        products = []

    return code, msg, [p for p in products if isinstance(p, dict)]


def main() -> int:
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("ERROR: faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")
        return 2

    print("ALIEXPRESS SMARTMATCH - PROBE")
    print("Endpoint:", ENDPOINT)
    print("API:", METHOD)
    print("Consultas:", len(QUERIES))
    print("No modifica SQLite, scanner ni Telegram.")
    print()

    for q in QUERIES:
        print(f"=== {q} ===")
        try:
            code, msg, products = query(q)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            print()
            continue

        print(f"resp_code={code} | resp_msg={msg} | resultados={len(products)}")
        for i, p in enumerate(products[:5], 1):
            print(f"{i}. {p.get('product_title', '<sin título>')}")
            print(
                "   "
                f"id={p.get('product_id', 'n/d')} | "
                f"precio={p.get('target_app_sale_price') or p.get('app_sale_price') or p.get('target_sale_price') or p.get('sale_price', 'n/d')} | "
                f"original={p.get('target_original_price') or p.get('original_price', 'n/d')} | "
                f"desc={p.get('discount', 'n/d')}"
            )
            print(
                "   "
                f"rating={p.get('evaluate_rate', 'n/d')} | "
                f"ventas={p.get('lastest_volume', 'n/d')} | "
                f"cat1={p.get('first_level_category_name', 'n/d')} | "
                f"cat2={p.get('second_level_category_name', 'n/d')}"
            )
            print(
                "   "
                f"affiliate={'OK' if p.get('promotion_link') else 'NO'} | "
                f"image={'OK' if p.get('product_main_image_url') else 'NO'}"
            )
        print()

    print("FIN SMARTMATCH.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
