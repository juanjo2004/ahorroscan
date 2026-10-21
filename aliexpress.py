import json
import os
import time
import hmac
import hashlib
import requests

from models import Offer
from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID

API_URL = "https://eco.taobao.com/router/rest"
API_METHOD = "aliexpress.affiliate.product.query"

def _timestamp_gmt8():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def generar_firma(params: dict, secret: str, api_name: str) -> str:
    items = []
    for key in sorted(params.keys()):
        if key == "sign":
            continue
        value = params[key]
        if value is None or value == "":
            continue
        items.append(f"{key}{value}")
    payload = api_name + "".join(items)
    return hmac.new(secret.encode("utf-8"),
                    payload.encode("utf-8"),
                    hashlib.sha256).hexdigest().upper()

def _parse_float(value):
    if value is None:
        return None
    try:
        s = str(value).strip().replace(" ", "")
        s = s.replace(",", ".")
        return float(s)
    except (TypeError, ValueError):
        return None

def buscar(keywords="nvme 1tb", limite=5, categoria=None):
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("[ALIEXPRESS] Credenciales/Tracking ID no configurados. Se omite.")
        return []

    fields = ",".join([
        "product_id", "product_title", "product_main_image_url",
        "product_detail_url", "promotion_link", "sale_price",
        "sale_price_currency", "original_price", "original_price_currency",
        "target_sale_price", "target_sale_price_currency",
        "target_original_price", "target_original_price_currency",
        "commission_rate", "discount", "evaluate_rate", "lastest_volume",
        "first_level_category_name", "second_level_category_name"
    ])

    params = {
        "app_key": ALI_APP_KEY,
        "format": "json",
        "method": API_METHOD,
        "sign_method": "hmac",
        "timestamp": _timestamp_gmt8(),
        "v": "2.0",
        "fields": fields,
        "keywords": keywords,
        "page_no": "1",
        "page_size": str(max(1, min(int(limite), 50))),
        "target_currency": "EUR",
        "target_language": "ES",
        "tracking_id": ALI_TRACKING_ID,
        "ship_to_country": "ES",
    }

    params["sign"] = generar_firma(params, ALI_APP_SECRET, API_METHOD)

    try:
        r = requests.post(API_URL, data=params, timeout=15)
        print(f"[ALIEXPRESS] HTTP {r.status_code} para '{keywords}'")
        data = r.json()

        if "error_response" in data:
            err = data["error_response"]
            print(f"[ALIEXPRESS] API {err.get('code')}: {err.get('msg') or err.get('message')}")
            return []

        # Algunas respuestas pueden venir envueltas de forma diferente.
        root = data.get("aliexpress_affiliate_product_query_response", {})
        resp = root.get("resp_result", root)
        if isinstance(resp, dict) and resp.get("resp_code") not in (None, 200, "200"):
            print(f"[ALIEXPRESS] resp_code={resp.get('resp_code')} msg={resp.get('resp_msg')}")
            return []

        result = resp.get("result", {}) if isinstance(resp, dict) else {}
        products_obj = result.get("products", {}) if isinstance(result, dict) else {}
        products = products_obj.get("product", []) if isinstance(products_obj, dict) else products_obj
        if isinstance(products, dict):
            products = [products]
        if not products:
            print(f"[ALIEXPRESS] 0 productos para '{keywords}'")
            return []

        offers = []
        for item in products[:limite]:
            sale = _parse_float(item.get("target_sale_price"))
            if sale is None:
                sale = _parse_float(item.get("sale_price"))
            original = _parse_float(item.get("target_original_price"))
            if original is None:
                original = _parse_float(item.get("original_price"))

            if sale is None:
                continue

            discount = None
            if original and original > sale:
                discount = (original - sale) / original * 100

            image = item.get("product_main_image_url") or ""
            detail = item.get("product_detail_url") or ""
            affiliate = item.get("promotion_link") or detail
            ext_id = str(item.get("product_id") or detail or item.get("product_title") or "")

            offers.append(Offer(
                source="aliexpress",
                external_id=ext_id,
                title=item.get("product_title") or "Producto AliExpress",
                url=detail,
                affiliate_url=affiliate,
                image_url=image,
                current_price=sale,
                reference_price=original,
                discount_pct=discount,
                rating=None,
                reviews=None,
                category=categoria,
            ))

        print(f"[ALIEXPRESS] Productos interpretados: {len(offers)}")
        return offers
    except Exception as exc:
        print(f"[ALIEXPRESS] EXCEPCIÓN: {exc}")
        return []
