#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import requests

from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID


ENDPOINT = "https://de-api.aliexpress.com/router/rest"
METHOD = "aliexpress.affiliate.product.query"
KEYWORDS = "nvme 1tb"


def now_gmt8() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


def sign_top(params: dict[str, str], secret: str) -> str:
    # AliExpress/TOP Affiliate API: ASCII-sort keys, concatenate key+value,
    # then HMAC-MD5 with App Secret. Return uppercase hexadecimal.
    payload = "".join(
        f"{k}{params[k]}"
        for k in sorted(params)
        if params[k] is not None and params[k] != ""
    )
    digest = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.md5,
    ).hexdigest().upper()
    return digest


def main() -> int:
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("ERROR: faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")
        return 2

    params = {
        "method": METHOD,
        "app_key": str(ALI_APP_KEY),
        "timestamp": now_gmt8(),
        "format": "json",
        "v": "2.0",
        "sign_method": "hmac",
        "keywords": KEYWORDS,
        "page_no": "1",
        "page_size": "5",
        "target_currency": "EUR",
        "target_language": "ES",
        "tracking_id": str(ALI_TRACKING_ID),
        "ship_to_country": "ES",
    }

    params["sign"] = sign_top(params, str(ALI_APP_SECRET))

    print(f"Probando endpoint EU de AliExpress con: '{KEYWORDS}'")
    print("Endpoint: https://de-api.aliexpress.com/router/rest")
    print("App Key presente: SÍ")
    print("Tracking ID presente: SÍ")
    print("No se muestran secretos ni firmas.")

    try:
        resp = requests.post(
            ENDPOINT,
            data=params,
            timeout=25,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    except requests.RequestException as exc:
        print(f"ERROR de conexión: {type(exc).__name__}: {exc}")
        return 3

    print(f"HTTP: {resp.status_code}")

    try:
        data = resp.json()
    except ValueError:
        print("ERROR: la respuesta no es JSON.")
        print(resp.text[:1200])
        return 4

    # Print only the high-level result, not credentials/signature.
    body = data.get("aliexpress_affiliate_product_query_response", data)

    if isinstance(body, dict):
        result = body.get("result", body)
        resp_obj = result.get("resp_result", result) if isinstance(result, dict) else result
    else:
        resp_obj = body

    # Common TOP error shape.
    if isinstance(resp_obj, dict):
        resp_code = resp_obj.get("resp_code")
        resp_msg = resp_obj.get("resp_msg")
        if resp_code is not None or resp_msg:
            print(f"resp_code: {resp_code}")
            print(f"resp_msg: {resp_msg}")

        # Try the common product list paths.
        products = None
        candidates = [
            resp_obj.get("result_list"),
            resp_obj.get("products"),
        ]

        # Some responses nest under result_list -> result.
        if isinstance(resp_obj.get("result_list"), dict):
            rl = resp_obj["result_list"]
            candidates.extend([
                rl.get("result"),
                rl.get("products"),
            ])

        for candidate in candidates:
            if isinstance(candidate, list):
                products = candidate
                break
            if isinstance(candidate, dict):
                for key in ("products", "product", "result"):
                    value = candidate.get(key)
                    if isinstance(value, list):
                        products = value
                        break
                if products is not None:
                    break

        # Generic error extraction.
        if "code" in resp_obj and resp_obj.get("code") not in (0, "0", None):
            print(f"API code: {resp_obj.get('code')}")
        if "msg" in resp_obj and resp_obj.get("msg"):
            print(f"API msg: {resp_obj.get('msg')}")

        if products:
            print(f"Productos recibidos: {len(products)}")
            first = products[0]
            if isinstance(first, dict):
                title = first.get("product_title") or first.get("productTitle") or "<sin título>"
                sale = first.get("target_sale_price") or first.get("sale_price") or first.get("targetSalePrice")
                original = first.get("original_price") or first.get("originalPrice")
                promo = first.get("promotion_link") or first.get("promotionLink")
                image = first.get("product_main_image_url") or first.get("productMainImageUrl")
                print(f"1. {title}")
                print(f"   precio={sale} | original={original}")
                print(f"   affiliate_url={'OK' if promo else 'NO'} | image={'OK' if image else 'NO'}")
            print("OK: el endpoint EU responde con productos.")
            return 0

    # If there is no clear product list, show a compact, redacted structure.
    print("Productos recibidos: 0")
    print("Respuesta resumida:", repr(data)[:1800])
    print("ERROR: el endpoint EU no devolvió productos.")
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
