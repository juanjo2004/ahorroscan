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
SDK_VERSION = "iop44-sdk-typescript-20231021"
TOKEN_FILE = Path("data/aliexpress_token.json")


def sign(params: dict[str, str], secret: str) -> str:
    # This mirrors the current ae_sdk signing logic for migrated TOP APIs:
    # sort all params by key, concatenate key+value, HMAC-SHA256.
    canonical = "".join(
        key + str(value)
        for key, value in sorted(params.items())
        if value is not None and str(value) != ""
    )
    return hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


def main() -> int:
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("ERROR: faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")
        return 2

    if not TOKEN_FILE.exists():
        print("ERROR: no existe data/aliexpress_token.json")
        return 3

    token_data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    access_token = token_data.get("access_token")
    if not access_token:
        print("ERROR: el archivo de token no contiene access_token")
        return 4

    params = {
        "app_key": str(ALI_APP_KEY),
        "session": str(access_token),
        "timestamp": str(int(time.time())) + "000",
        "sign_method": "sha256",
        "partner_id": SDK_VERSION,
        "method": METHOD,
        "simplify": "false",
        "format": "json",
        "v": "2.0",
        "keywords": "nvme",
        "page_no": "1",
        "page_size": "1",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
    }

    params["sign"] = sign(params, str(ALI_APP_SECRET))

    print("Probando AliExpress Affiliate API autenticada")
    print(f"Endpoint: {ENDPOINT}")
    print(f"API: {METHOD}")
    print("Consulta: nvme")
    print("session presente: SÍ")
    print("sign_method: sha256")
    print("No se muestran token, secreto ni firma.")

    try:
        response = requests.post(
            ENDPOINT,
            data=params,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
    except requests.RequestException as exc:
        print(f"ERROR de conexión: {type(exc).__name__}: {exc}")
        return 5

    print(f"HTTP: {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        print("ERROR: respuesta no JSON")
        print(response.text[:2000])
        return 6

    if "error_response" in data:
        err = data["error_response"]
        print("Error response:")
        if isinstance(err, dict):
            for key in ("code", "msg", "sub_code", "request_id"):
                if key in err:
                    print(f"  {key}: {err[key]}")
        print("Productos recibidos: 0")
        return 7

    root = data.get("aliexpress_affiliate_product_query_response")
    if isinstance(root, dict):
        rr = root.get("resp_result", {})
        if isinstance(rr, dict):
            result = rr.get("result", {})
            if isinstance(result, dict):
                products_obj = result.get("products", {})
                if isinstance(products_obj, dict):
                    products = products_obj.get("product", [])
                    if isinstance(products, list) and products:
                        print(f"Productos recibidos: {len(products)}")
                        p = products[0]
                        if isinstance(p, dict):
                            title = p.get("product_title", "<sin título>")
                            price = p.get("target_sale_price") or p.get("sale_price")
                            original = p.get("original_price")
                            promotion = p.get("promotion_link")
                            image = p.get("product_main_image_url")
                            print(f"Título: {title}")
                            print(f"Precio: {price}")
                            print(f"Original: {original}")
                            print(f"Affiliate URL: {'OK' if promotion else 'NO'}")
                            print(f"Imagen: {'OK' if image else 'NO'}")
                        print("OK: API autenticada respondió con un producto.")
                        return 0

    print("Productos recibidos: 0")
    print("Respuesta resumida:", repr(data)[:3000])
    return 8


if __name__ == "__main__":
    raise SystemExit(main())
