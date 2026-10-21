#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import requests

from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID

METHOD = "aliexpress.affiliate.productquery"
REQ_KEY = "param_aeop_aep_product_query_req"
REQ = {
    "keywords": "nvme",
    "page_no": 1,
    "page_size": 1,
    "tracking_id": str(ALI_TRACKING_ID),
}

# The user's AliExpress API Access Log showed env=PROD-GLOBAL / AE_GLOBAL,
# method=aliexpress.affiliate.productquery, sign_method=md5 and the exact
# business request parameter below. We probe the REST path variants that map
# to that log notation.
ENDPOINTS = [
    "https://api-sg.aliexpress.com/rest/aliexpress.affiliate.productquery",
    "https://api-sg.aliexpress.com/restaliexpress.affiliate.productquery",
]


def sign_md5(params: dict[str, str], secret: str) -> str:
    # TOP-style MD5 signing: ASCII-sort keys, concatenate key+value, MD5(secret+payload+secret).
    payload = "".join(
        key + str(params[key])
        for key in sorted(params)
        if params[key] is not None and str(params[key]) != ""
    )
    raw = secret + payload + secret
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def sign_hmac_md5(params: dict[str, str], secret: str) -> str:
    # HMAC variant, kept as a fallback because the current gateway family has
    # both legacy TOP and HMAC implementations in circulation.
    payload = "".join(
        key + str(params[key])
        for key in sorted(params)
        if params[key] is not None and str(params[key]) != ""
    )
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.md5,
    ).hexdigest().upper()


def run(endpoint: str, signer_name: str, signer) -> None:
    params = {
        "app_key": str(ALI_APP_KEY),
        "method": METHOD,
        "v": "2.0",
        "sign_method": "md5",
        "format": "json",
        "timestamp": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        REQ_KEY: json.dumps(REQ, separators=(",", ":"), ensure_ascii=False),
    }
    params["sign"] = signer(params, str(ALI_APP_SECRET))

    print(f"\n--- {endpoint} | firma={signer_name} ---")
    try:
        r = requests.post(
            endpoint,
            data=params,
            timeout=25,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
    except requests.RequestException as exc:
        print(f"ERROR de conexión: {type(exc).__name__}: {exc}")
        return

    print("HTTP:", r.status_code)
    try:
        data = r.json()
    except ValueError:
        print("Respuesta no JSON:", r.text[:1200])
        return

    if isinstance(data, dict) and "error_response" in data:
        err = data["error_response"]
        if isinstance(err, dict):
            print("code:", err.get("code"))
            print("msg:", err.get("msg"))
            print("sub_code:", err.get("sub_code"))
            print("request_id:", err.get("request_id"))
        return

    print("Respuesta resumida:", repr(data)[:2200])


def main() -> int:
    if not ALI_APP_KEY or not ALI_APP_SECRET or not ALI_TRACKING_ID:
        print("ERROR: faltan ALI_APP_KEY, ALI_APP_SECRET o ALI_TRACKING_ID en .env")
        return 2

    print("Diagnóstico REST AliExpress basado literalmente en API Access Log")
    print("method: aliexpress.affiliate.productquery")
    print("sign_method: md5")
    print("business param:", REQ_KEY)
    print("No se muestran secretos ni firmas.")

    for endpoint in ENDPOINTS:
        run(endpoint, "TOP-MD5", sign_md5)
        run(endpoint, "HMAC-MD5", sign_hmac_md5)

    print("\nFIN diagnóstico REST. No modifica SQLite, scanner ni Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
