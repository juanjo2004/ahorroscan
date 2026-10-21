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
    ("raton gaming", ("raton", "gaming")),
    ("ssd nvme", ("ssd", "nvme")),
    ("memoria ram ddr5", ("memoria", "ram", "ddr5")),
    ("monitor 4k", ("monitor", "4k")),
    ("teclado mecanico", ("teclado", "mecanico")),
]

def sign(params: dict[str, str]) -> str:
    canonical = "".join(
        k + str(v)
        for k, v in sorted(params.items())
        if v is not None and str(v) != ""
    )
    return hmac.new(
        str(ALI_APP_SECRET).encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()

def query(keyword: str) -> list[dict]:
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("Falta access_token en data/aliexpress_token.json")

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
        "page_size": "20",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
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

    root = data.get("aliexpress_affiliate_product_query_response", {})
    rr = root.get("resp_result", {}) if isinstance(root, dict) else {}
    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products_obj = result.get("products", {}) if isinstance(result, dict) else {}
    products = products_obj.get("product", []) if isinstance(products_obj, dict) else []
    return [p for p in products if isinstance(p, dict)] if isinstance(products, list) else []

def normalize(s: str) -> str:
    return " ".join((s or "").lower().replace("-", " ").split())

def relevant(title: str, required: tuple[str, ...]) -> tuple[bool, list[str]]:
    t = normalize(title)
    hits = [term for term in required if term in t]
    return len(hits) >= max(1, len(required) - 1), hits

def main() -> int:
    print("ALIEXPRESS PRODUCT.QUERY - PRUEBA DE RELEVANCIA")
    print("5 consultas x 20 resultados. No modifica SQLite ni Telegram.")
    for keyword, required in QUERIES:
        print(f"\n=== {keyword} ===")
        try:
            products = query(keyword)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            continue
        good = 0
        print(f"Resultados API: {len(products)}")
        for i, p in enumerate(products, 1):
            title = str(p.get("product_title", ""))
            ok, hits = relevant(title, required)
            good += int(ok)
            price = p.get("target_sale_price") or p.get("sale_price") or p.get("app_sale_price")
            print(f"{i:02d}. [{'OK' if ok else 'NO'}] {title}")
            print(
                f"    precio={price} | desc={p.get('discount','n/d')} | "
                f"rating={p.get('evaluate_rate','n/d')} | ventas={p.get('lastest_volume','n/d')}"
            )
            print(
                f"    cat={p.get('first_level_category_name','n/d')} > "
                f"{p.get('second_level_category_name','n/d')} | hits={','.join(hits) or '-'}"
            )
        rate = good / len(products) * 100 if products else 0.0
        print(f"Relevancia heurística por título: {good}/{len(products)} = {rate:.1f}%")
    print("\nFIN.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
