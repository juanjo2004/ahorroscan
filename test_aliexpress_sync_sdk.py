#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

import requests

from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID

ENDPOINT = "https://api-sg.aliexpress.com/sync"
METHOD = "aliexpress.affiliate.product.query"
SDK_VERSION = "iop44-sdk-typescript-20231021"
KEYWORDS = "nvme 1tb"


def sign(secret: str, api: str, params: dict[str, str]) -> str:
    ordered = sorted(params)
    canonical = "".join(f"{k}{params[k]}" for k in ordered if params[k] != "")
    if "/" in api:
        canonical = api + canonical
    return hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


def main() -> int:
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("ERROR: faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")
        return 2

    params: dict[str, str] = {
        "app_key": str(ALI_APP_KEY),
        "sign_method": "sha256",
        "timestamp": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "partner_id": SDK_VERSION,
        "method": METHOD,
        "simplify": "false",
        "format": "json",
        "v": "2.0",
        "keywords": KEYWORDS,
        "page_no": "1",
        "page_size": "1",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
    }

    # No access token is invented or added. This probe tests the public
    # Affiliate Product Query call with the SDK's required system parameters.
    params["sign"] = sign(str(ALI_APP_SECRET), METHOD, params)

    print(f"Probando AliExpress /sync replicando el SDK con: '{KEYWORDS}'")
    print(f"Endpoint: {ENDPOINT}")
    print("sign_method: sha256")
    print(f"partner_id: {SDK_VERSION}")
    print("simplify: false")
    print("session presente: NO")
    print("No se muestran secretos ni la firma.")

    try:
        response = requests.post(
            ENDPOINT,
            data=params,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
    except requests.RequestException as exc:
        print(f"ERROR de conexión: {type(exc).__name__}: {exc}")
        return 3

    print(f"HTTP: {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        print("ERROR: respuesta no JSON.")
        print(response.text[:1800])
        return 4

    if "error_response" in data:
        err = data["error_response"]
        print("Error response:")
        if isinstance(err, dict):
            for key in ("code", "msg", "sub_code", "request_id"):
                if key in err:
                    print(f"  {key}: {err[key]}")
        print("Productos recibidos: 0")
        return 5

    root = data.get("aliexpress_affiliate_product_query_response")
    if isinstance(root, dict):
        rsp = root.get("resp_result", root)
        if isinstance(rsp, dict):
            result = rsp.get("result", {})
            if isinstance(result, dict):
                products_obj = result.get("products", {})
                if isinstance(products_obj, dict):
                    products = products_obj.get("product", [])
                    if isinstance(products, list) and products:
                        print(f"Productos recibidos: {len(products)}")
                        p = products[0]
                        if isinstance(p, dict):
                            print("Título:", p.get("product_title", "<sin título>"))
                            print(
                                "Precio:",
                                p.get("target_sale_price") or p.get("sale_price"),
                            )
                            print(
                                "Affiliate URL:",
                                "OK" if p.get("promotion_link") else "NO",
                            )
                            print(
                                "Imagen:",
                                "OK" if p.get("product_main_image_url") else "NO",
                            )
                        print("OK: /sync respondió con un producto.")
                        return 0

    print("Productos recibidos: 0")
    print("Respuesta resumida:", repr(data)[:2600])
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
