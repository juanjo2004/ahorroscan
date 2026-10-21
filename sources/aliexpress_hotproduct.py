"""Prueba aislada de aliexpress.affiliate.hotproduct.query.

No modifica el adaptador principal de V2. Usa el gateway TOP documentado por
AliExpress y la firma HMAC para comprobar si el App Key aprobado puede llamar
esta API del grupo Advanced/Promotion Creatives.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

import config

API_URL = "https://eco.taobao.com/router/rest"
METHOD = "aliexpress.affiliate.hotproduct.query"


def _timestamp_gmt8() -> str:
    gmt8 = timezone(timedelta(hours=8))
    return datetime.now(gmt8).strftime("%Y-%m-%d %H:%M:%S")


def _sign(params: Dict[str, Any], secret: str) -> str:
    # TOP hmac signing: ASCII-sort parameter names, concatenate key+value,
    # then HMAC-MD5 with the App Secret, uppercase hexadecimal digest.
    pairs = []
    for key, value in params.items():
        if key == "sign" or value is None:
            continue
        pairs.append((str(key), str(value)))
    pairs.sort(key=lambda item: item[0])
    raw = "".join(f"{key}{value}" for key, value in pairs)
    return hmac.new(
        secret.encode("utf-8"), raw.encode("utf-8"), hashlib.md5
    ).hexdigest().upper()


def _products(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    root = data
    wrapper = root.get("aliexpress_affiliate_hotproduct_query_response")
    if isinstance(wrapper, dict):
        root = wrapper
    resp = root.get("resp_result") if isinstance(root, dict) else None
    if isinstance(resp, dict):
        root = resp
    result = root.get("result") if isinstance(root, dict) else None
    if isinstance(result, dict):
        root = result

    products = root.get("products") if isinstance(root, dict) else None
    if isinstance(products, dict):
        products = products.get("product")
    if isinstance(products, list):
        return [p for p in products if isinstance(p, dict)]
    if isinstance(products, dict):
        return [products]
    return []


def query(keywords: str = "nvme 1tb", limit: int = 3) -> List[Dict[str, Any]]:
    app_key = os.getenv("ALI_APP_KEY", getattr(config, "ALI_APP_KEY", ""))
    app_secret = os.getenv("ALI_APP_SECRET", getattr(config, "ALI_APP_SECRET", ""))
    tracking_id = os.getenv("ALI_TRACKING_ID", getattr(config, "ALI_TRACKING_ID", ""))

    if not app_key or not app_secret or not tracking_id:
        raise RuntimeError("Faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")

    limit = max(1, min(int(limit), 50))
    fields = ",".join([
        "app_sale_price",
        "app_sale_price_currency",
        "commission_rate",
        "discount",
        "evaluate_rate",
        "lastest_volume",
        "original_price",
        "original_price_currency",
        "product_detail_url",
        "product_id",
        "product_main_image_url",
        "product_title",
        "promotion_link",
        "sale_price",
        "sale_price_currency",
        "target_app_sale_price",
        "target_original_price",
        "target_sale_price",
        "target_sale_price_currency",
    ])

    params: Dict[str, Any] = {
        "app_key": app_key,
        "format": "json",
        "method": METHOD,
        "sign_method": "hmac",
        "timestamp": _timestamp_gmt8(),
        "v": "2.0",
        "keywords": keywords,
        "page_no": 1,
        "page_size": limit,
        "fields": fields,
        "tracking_id": tracking_id,
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
        "sort": "SALE_PRICE_ASC",
    }
    params["sign"] = _sign(params, app_secret)

    response = requests.post(API_URL, data=params, timeout=25)
    print(f"[ALIEXPRESS HOTPRODUCT] HTTP {response.status_code} para '{keywords}'")

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except ValueError:
        print("[ALIEXPRESS HOTPRODUCT] Respuesta no JSON")
        return []

    err = data.get("error_response")
    if isinstance(err, dict):
        code = err.get("code", "?")
        msg = err.get("msg") or err.get("sub_msg") or "error desconocido"
        print(f"[ALIEXPRESS HOTPRODUCT] API {code}: {msg}")
        return []

    resp = data.get("aliexpress_affiliate_hotproduct_query_response")
    if isinstance(resp, dict):
        rr = resp.get("resp_result")
        if isinstance(rr, dict):
            code = rr.get("resp_code")
            msg = rr.get("resp_msg")
            if code not in (None, 200, "200"):
                print(f"[ALIEXPRESS HOTPRODUCT] resp_code {code}: {msg}")
                return []

    return _products(data)
