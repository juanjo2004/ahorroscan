#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID


ENDPOINT = "https://api-sg.aliexpress.com/sync"
TOKEN_FILE = Path("data/aliexpress_token.json")
METHOD = "aliexpress.affiliate.product.query"
PARTNER_ID = "iop44-sdk-typescript-20231021"


@dataclass(frozen=True)
class Rule:
    name: str
    queries: tuple[str, ...]
    query_boost: dict[str, int]
    core: tuple[str, ...]
    required: tuple[tuple[str, ...], ...]
    positive: tuple[str, ...]
    hard_negative: tuple[str, ...]
    soft_negative: tuple[str, ...]


RULES = (
    # ================================================================
    # AURICULARES BLUETOOTH
    # ================================================================
    Rule(
        "auriculares_bluetooth",
        (
            "auriculares bluetooth",
            "bluetooth earbuds",
            "wireless earbuds",
        ),
        {
            "auriculares bluetooth": 15,
            "bluetooth earbuds": 15,
            "wireless earbuds": 12,
        },
        (
            "auricular",
            "auriculares",
            "earbud",
            "earbuds",
            "earphone",
            "earphones",
            "headphone",
            "headphones",
        ),
        (
            ("bluetooth", "wireless", "tws"),
        ),
        (
            "anc",
            "cancelacion de ruido",
            "cancelación de ruido",
            "estereo",
            "estéreo",
            "hifi",
            "hi-fi",
            "llamadas",
            "deportivo",
            "deporte",
            "gaming",
        ),
        (
            "funda",
            "case",
            "estuche",
            "protector",
            "proteccion",
            "protección",
            "almohadilla",
            "almohadillas",
            "earpad",
            "earpads",
            "cable",
            "cables",
            "repuesto",
            "replacement",
            "adaptador",
            "soporte",
            "soportes",
            "gancho",
            "ganchos",
            "diadema de repuesto",
        ),
        (
            "accesorio",
            "accesorios",
        ),
    ),

    # ================================================================
    # CARGADORES GAN
    # ================================================================
    Rule(
        "cargador_gan",
        (
            "cargador gan",
            "gan charger",
            "gan pd charger",
        ),
        {
            "cargador gan": 15,
            "gan charger": 15,
            "gan pd charger": 12,
        },
        (
            "cargador",
            "charger",
            "adaptador de corriente",
            "power adapter",
        ),
        (
            ("gan",),
        ),
        (
            "usb-c",
            "usb c",
            "type-c",
            "type c",
            "pd",
            "power delivery",
            "carga rapida",
            "carga rápida",
            "fast charge",
            "65w",
            "67w",
            "100w",
            "120w",
            "140w",
            "160w",
            "200w",
            "240w",
        ),
        (
            "cable",
            "cables",
            "soporte",
            "soportes",
            "funda",
            "estuche",
            "repuesto",
            "replacement",
            "enchufe de coche",
            "adaptador usb",
            "adaptador de audio",
            "hub",
            "dock",
            "estacion de carga",
            "estación de carga",
            "cargador inalambrico",
            "cargador inalámbrico",
        ),
        (
            "accesorio",
            "accesorios",
        ),
    ),

    # ================================================================
    # MICROFONO USB
    # ================================================================
    Rule(
        "microfono_usb",
        (
            "gaming microphone usb",
            "microfono condensador usb",
            "streaming microphone usb",
        ),
        {
            "gaming microphone usb": 18,
            "microfono condensador usb": 15,
            "streaming microphone usb": 15,
        },
        (
            "microfono",
            "micrófono",
            "microphone",
        ),
        (
            (
                "usb",
                "usb-c",
                "type-c",
                "type c",
            ),
        ),
        (
            "condensador",
            "condenser",
            "streaming",
            "podcast",
            "vlog",
            "grabacion",
            "grabación",
            "voz",
            "pc",
            "ordenador",
            "computadora",
            "gaming",
            "gamer",
            "rgb",
            "ganancia",
            "gain",
            "mute",
            "silencio",
            "cancelacion de ruido",
            "cancelación de ruido",
        ),
        (
            "auriculares bluetooth",
            "auriculares inalambricos",
            "auriculares inalámbricos",
            "auriculares tws",
            "bluetooth earbuds",
            "wireless earbuds",
            "earbud",
            "earbuds",
            "headphone",
            "headphones",
            "lavalier",
            "solapa",
            "cable",
            "cables",
            "soporte",
            "soportes",
            "funda",
            "fundas",
            "estuche",
            "estuches",
            "repuesto",
            "replacement",
            "adaptador",
            "mezclador",
            "mezcla",
            "mixer",
            "interfaz de audio",
            "audio interface",
            "consola de mezcla",
        ),
        (
            "brazo",
            "brazos",
            "shock mount",
            "pop filter",
            "filtro pop",
            "espuma",
            "windshield",
            "accesorio",
            "accesorios",
        ),
    ),
)


def norm(s: str) -> str:
    t = (s or "").lower()

    table = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
        }
    )

    return " ".join(
        t.translate(table).split()
    )


def sign(params: dict[str, str]) -> str:
    canonical = "".join(
        k + str(params[k])
        for k in sorted(params)
        if params[k] not in (None, "")
    )

    return hmac.new(
        str(ALI_APP_SECRET).encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest().upper()


def fetch(keyword: str) -> list[dict]:
    token = json.loads(
        TOKEN_FILE.read_text(
            encoding="utf-8"
        )
    ).get("access_token")

    if not token:
        raise RuntimeError(
            "Falta access_token"
        )

    params = {
        "app_key": str(ALI_APP_KEY),
        "session": token,
        "format": "json",
        "method": METHOD,
        "partner_id": PARTNER_ID,
        "sign_method": "sha256",
        "simplify": "false",
        "timestamp": str(
            time.time_ns() // 1_000_000
        ),
        "v": "2.0",
        "keywords": keyword,
        "page_no": "1",
        "page_size": "20",
        "tracking_id": str(
            ALI_TRACKING_ID
        ),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
    }

    params["sign"] = sign(params)

    response = requests.post(
        ENDPOINT,
        data=params,
        timeout=30,
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded;charset=utf-8"
        },
    )

    response.raise_for_status()

    data = response.json()

    rr = (
        data.get(
            "aliexpress_affiliate_product_query_response",
            {},
        )
        .get(
            "resp_result",
            {},
        )
    )

    if isinstance(rr, dict) and rr.get(
        "resp_code"
    ) not in (
        None,
        200,
        "200",
    ):
        raise RuntimeError(
            f"API {rr.get('resp_code')}: "
            f"{rr.get('resp_msg')}"
        )

    result = (
        rr.get("result", {})
        if isinstance(rr, dict)
        else {}
    )

    products = (
        result.get("products", {})
        .get("product", [])
        if isinstance(result, dict)
        else []
    )

    if isinstance(products, dict):
        products = [products]

    return (
        products
        if isinstance(products, list)
        else []
    )


def contains(
    text: str,
    terms: tuple[str, ...],
) -> list[str]:
    return [
        term
        for term in terms
        if norm(term) in text
    ]


def score_product(
    product: dict,
    rule: Rule,
    query: str,
) -> tuple[int, list[str]]:
    title = norm(
        str(
            product.get(
                "product_title",
                "",
            )
        )
    )

    category = norm(
        f"{product.get('first_level_category_name', '')} "
        f"{product.get('second_level_category_name', '')}"
    )

    reasons: list[str] = []

    # ------------------------------------------------------------
    # CORE
    # ------------------------------------------------------------
    if not contains(
        title,
        rule.core,
    ):
        return 0, ["sin_core"]

    score = 35

    reasons.append(
        "producto_principal"
    )

    # ------------------------------------------------------------
    # QUERY BOOST
    # ------------------------------------------------------------
    query_boost = rule.query_boost.get(
        query,
        0,
    )

    score += query_boost

    if query_boost:
        reasons.append(
            f"consulta_especifica+{query_boost}"
        )

    # ------------------------------------------------------------
    # REQUIRED
    # ------------------------------------------------------------
    for group in rule.required:
        hits = contains(
            title,
            group,
        )

        if hits:
            score += 15

            reasons.append(
                "requisito:"
                + ",".join(hits)
            )
        else:
            score -= 15

            reasons.append(
                "falta:"
                + "/".join(group)
            )

    # ------------------------------------------------------------
    # POSITIVE
    # ------------------------------------------------------------
    positive = contains(
        title,
        rule.positive,
    )

    score += min(
        30,
        5 * len(positive),
    )

    if positive:
        reasons.append(
            "positivos:"
            + ",".join(
                positive[:8]
            )
        )

    # ------------------------------------------------------------
    # HARD NEGATIVE
    # ------------------------------------------------------------
    negative = contains(
        title,
        rule.hard_negative,
    )

    if negative:
        score -= min(
            95,
            75 + 8 * (len(negative) - 1),
        )

        reasons.append(
            "bloqueos:"
            + ",".join(
                negative[:8]
            )
        )

    # ------------------------------------------------------------
    # SOFT NEGATIVE
    # ------------------------------------------------------------
    soft = contains(
        title,
        rule.soft_negative,
    )

    if soft:
        score -= min(
            10,
            5 * len(soft),
        )

        reasons.append(
            "avisos:"
            + ",".join(
                soft[:5]
            )
        )

    # ------------------------------------------------------------
    # CATEGORY BOOST
    # ------------------------------------------------------------
    if any(
        x in category
        for x in (
            "perifericos",
            "componentes de ordenadores",
            "audio",
            "electronica",
        )
    ):
        score += 10

        reasons.append(
            "categoria_util"
        )

    return (
        max(
            0,
            min(
                100,
                score,
            ),
        ),
        reasons,
    )


def label(score: int) -> str:
    if score >= 80:
        return "MUY RELEVANTE"

    if score >= 70:
        return "RELEVANTE"

    if score >= 55:
        return "DUDOSO"

    return "NO RELEVANTE"


def main() -> None:
    print(
        "ALIEXPRESS - QUERY + CLASSIFIER "
        "V6.3.3 EXPERIMENTAL"
    )

    print(
        "Tres familias nuevas. "
        "Sin tocar SQLite ni producción.\n"
    )

    for rule in RULES:
        print(
            "=" * 90
        )

        print(
            f"===== {rule.name} ====="
        )

        for query in rule.queries:
            try:
                products = fetch(query)

            except Exception as exc:
                print(
                    f"\nQUERY: {query}"
                )

                print(
                    f"ERROR: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                continue

            ranked = []

            for product in products:
                score, why = score_product(
                    product,
                    rule,
                    query,
                )

                ranked.append(
                    (
                        score,
                        product,
                        why,
                    )
                )

            ranked.sort(
                key=lambda x: x[0],
                reverse=True,
            )

            print(
                f"\nQUERY: {query} | "
                f"resultados={len(ranked)}"
            )

            for i, (
                score,
                product,
                why,
            ) in enumerate(
                ranked[:10],
                1,
            ):
                title = product.get(
                    "product_title",
                    "<sin titulo>",
                )

                print(
                    f"{i:02d}. "
                    f"[{score:3d}] "
                    f"{label(score)} | "
                    f"{title}"
                )

                print(
                    "    "
                    f"precio="
                    f"{product.get('target_sale_price') or product.get('sale_price') or product.get('app_sale_price') or 'n/d'} "
                    f"| rating="
                    f"{product.get('evaluate_rate', 'n/d')} "
                    f"| ventas="
                    f"{product.get('lastest_volume', 'n/d')}"
                )

                print(
                    "    "
                    + ";".join(why)
                )

            print(
                "TOP10 >=70:",
                sum(
                    1
                    for score, _, _ in ranked[:10]
                    if score >= 70
                ),
                "| TOP10 >=80:",
                sum(
                    1
                    for score, _, _ in ranked[:10]
                    if score >= 80
                ),
            )

    print(
        "\nFIN. Experimento V6.3.3 aislado."
    )


if __name__ == "__main__":
    main()
