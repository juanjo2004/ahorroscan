#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import re
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
class Profile:
    name: str
    queries: tuple[str, ...]
    main_terms: tuple[str, ...]
    positive: tuple[str, ...]
    hard_negative: tuple[str, ...]
    query_boost: dict[str, int]


PROFILES = (
    Profile(
        "raton_gaming",
        ("raton gaming", "gaming mouse", "raton gaming inalambrico",
         "wireless gaming mouse", "mouse optico gaming"),
        ("raton", "ratón", "mouse"),
        ("gaming", "gamer", "juegos", "inalambrico", "inalámbrico", "wireless",
         "bluetooth", "2.4g", "sensor", "dpi", "optico", "óptico", "rgb",
         "ergonomico", "ergonómico", "paw3395", "26000dpi", "8k", "polling"),
        ("patines", "skates", "feet", "pies de repuesto", "grip", "agarre",
         "cinta de agarre", "cable de carga", "cable de datos", "microinterruptor",
         "encoder", "codificador", "repuesto", "replacement", "estuche", "funda",
         "alfombrilla", "almohadilla", "case", "adaptador", "adaptadores",
         "pegatina", "pegatinas", "pieza", "piezas"),
        {
            "raton gaming": 0,
            "gaming mouse": 8,
            "raton gaming inalambrico": 12,
            "wireless gaming mouse": 15,
            "mouse optico gaming": 12,
        },
    ),
    Profile(
        "ssd_nvme",
        ("ssd nvme", "ssd nvme 1tb m2", "m2 nvme ssd 1tb",
         "pcie 4.0 nvme ssd", "2280 nvme ssd"),
        ("ssd", "nvme", "unidad de estado sólido", "unidad de estado solido"),
        ("m.2", "m 2", "pcie", "pci-e", "gen3", "gen4", "gen5",
         "2280", "1tb", "2tb", "4tb", "500gb", "512gb", "256gb",
         "mb/s", "7400", "7000", "10000", "14000", "interno", "interna"),
        ("disipador", "disipador de calor", "heatsink", "cooler", "radiador",
         "mini pc", "laptop", "notebook", "portátil", "portatil", "carcasa",
         "enclosure", "case", "adaptador", "adapter", "conmutador", "switch",
         "soporte", "base", "dock", "estuche", "cable", "cables", "externo",
         "external", "usb"),
        {
            "ssd nvme": 0,
            "ssd nvme 1tb m2": 12,
            "m2 nvme ssd 1tb": 15,
            "pcie 4.0 nvme ssd": 15,
            "2280 nvme ssd": 8,
        },
    ),
    Profile(
        "monitor_4k",
        ("monitor 4k", "monitor 4k 27 pulgadas", "4k gaming monitor",
         "uhd monitor 27", "ips 4k monitor"),
        ("monitor", "pantalla", "display"),
        ("4k", "uhd", "27", "24", "25", "32", "34", "144hz", "165hz",
         "180hz", "240hz", "120hz", "hdmi", "displayport", "ips", "va",
         "oled", "freesync", "g-sync", "g sync", "hdr", "vesa", "3840x2160"),
        ("cámara", "camara", "dashcam", "coche", "lente", "lens", "gafas",
         "smart glasses", "proyector", "extensor hdmi", "adaptador hdmi",
         "capturadora", "transmisor", "transmisión", "cable", "fuente de alimentación",
         "panel de repuesto", "pantalla de repuesto", "controladora", "placa controladora"),
        {
            "monitor 4k": 0,
            "monitor 4k 27 pulgadas": 15,
            "4k gaming monitor": 8,
            "uhd monitor 27": 15,
            "ips 4k monitor": 12,
        },
    ),
    Profile(
        "teclado_mecanico",
        ("teclado mecanico", "mechanical keyboard", "teclado gaming mecanico",
         "87 key mechanical keyboard", "75 percent mechanical keyboard"),
        ("teclado", "keyboard"),
        ("mecánico", "mecanico", "mechanical", "hot-swap", "hotswap", "qmk",
         "via", "rgb", "bluetooth", "wireless", "2.4g", "pbt", "87 teclas",
         "104 teclas", "108 teclas", "75%", "65%", "60%", "tkl", "layout",
         "ansi", "iso", "switch"),
        ("alfombrilla", "mouse pad", "pegatina", "sticker", "estuche", "funda",
         "soporte", "stand", "mesa", "organizador", "llavero", "juguete",
         "keycap", "keycaps", "tecla suelta", "switches", "interruptores",
         "cable de teclado", "placa de posicionamiento", "repuesto"),
        {
            "teclado mecanico": 0,
            "mechanical keyboard": 5,
            "teclado gaming mecanico": 10,
            "87 key mechanical keyboard": 12,
            "75 percent mechanical keyboard": 18,
        },
    ),
)


def norm(s: str) -> str:
    t = (s or "").lower()
    table = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"})
    return " ".join(t.translate(table).split())


def sign(params: dict[str, str]) -> str:
    canonical = "".join(k + str(params[k]) for k in sorted(params) if params[k] not in (None, ""))
    return hmac.new(str(ALI_APP_SECRET).encode(), canonical.encode(), hashlib.sha256).hexdigest().upper()


def fetch(keyword: str) -> list[dict]:
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    if not token:
        raise RuntimeError("Falta access_token en data/aliexpress_token.json")
    p = {
        "app_key": str(ALI_APP_KEY), "session": token, "format": "json",
        "method": METHOD, "partner_id": PARTNER_ID, "sign_method": "sha256",
        "simplify": "false", "timestamp": str(int(time.time() * 1000)),
        "v": "2.0", "keywords": keyword, "page_no": "1", "page_size": "20",
        "tracking_id": str(ALI_TRACKING_ID), "target_currency": "EUR",
        "target_language": "ES", "ship_to_country": "ES",
    }
    p["sign"] = sign(p)
    r = requests.post(ENDPOINT, data=p, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"})
    r.raise_for_status()
    data = r.json()
    rr = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products = result.get("products", {}).get("product", []) if isinstance(result, dict) else []
    return products if isinstance(products, list) else []


def score(p: dict, profile: Profile, query: str) -> tuple[int, str]:
    title = norm(str(p.get("product_title", "")))
    cat = norm(f"{p.get('first_level_category_name','')} {p.get('second_level_category_name','')}")

    if not any(norm(x) in title for x in profile.main_terms):
        return 0, "sin_producto_principal"

    s = 35
    reasons = ["producto_principal"]
    qboost = profile.query_boost.get(query, 0)
    s += qboost
    if qboost:
        reasons.append(f"precision_consulta+{qboost}")

    # Positive evidence. First hit gives a meaningful boost, not all hits equally.
    positives = [x for x in profile.positive if norm(x) in title]
    s += min(30, 6 * len(positives))
    if positives:
        reasons.append("señales:" + ",".join(positives[:7]))

    # Strong penalties for accessories or wrong product class.
    negatives = [x for x in profile.hard_negative if norm(x) in title]
    if negatives:
        s -= min(85, 65 + 8 * (len(negatives) - 1))
        reasons.append("bloqueos:" + ",".join(negatives[:7]))

    # Category helps, but never decides alone.
    if any(x in cat for x in ("perifericos", "componentes de ordenadores")):
        s += 10
        reasons.append("categoria_util")

    # Specific sanity rules.
    if profile.name == "raton_gaming":
        if not any(x in title for x in ("gaming", "gamer", "juegos")):
            s = min(s, 45)
    elif profile.name == "ssd_nvme":
        if any(x in title for x in ("mini pc", "laptop", "notebook", "portatil", "portátil", "carcasa", "enclosure", "disipador")):
            s = min(s, 10)
        if not any(x in title for x in ("tb", "gb")):
            s = min(s, 55)
    elif profile.name == "monitor_4k":
        if not any(x in title for x in ("monitor", "pantalla", "display")):
            return 0, "sin_tipo_monitor"
        if not any(x in title for x in ("4k", "uhd")):
            s = min(s, 50)
    elif profile.name == "teclado_mecanico":
        if not any(x in title for x in ("teclado", "keyboard")):
            return 0, "sin_tipo_teclado"
        if not any(x in title for x in ("mecanico", "mecánico", "mechanical")):
            s = min(s, 45)

    return max(0, min(100, s)), ";".join(reasons)


def label(s: int) -> str:
    if s >= 80:
        return "MUY RELEVANTE"
    if s >= 70:
        return "RELEVANTE"
    if s >= 55:
        return "DUDOSO"
    return "NO RELEVANTE"


def main():
    print("ALIEXPRESS - QUERY + CLASSIFIER V4")
    print("La consulta aporta evidencia; accesorios/repuestos se bloquean.")
    print("No modifica SQLite, scanner, histórico ni Telegram.\n")

    for profile in PROFILES:
        print(f"===== {profile.name} =====")
        for query in profile.queries:
            try:
                products = fetch(query)
            except Exception as exc:
                print(f"\nQUERY: {query}\nERROR: {type(exc).__name__}: {exc}")
                continue

            ranked=[]
            for p in products:
                s, why = score(p, profile, query)
                ranked.append((s,p,why))
            ranked.sort(key=lambda x:x[0], reverse=True)

            print(f"\nQUERY: {query} | resultados={len(ranked)}")
            for i,(s,p,why) in enumerate(ranked[:10],1):
                print(f"{i:02d}. [{s:3d}] {label(s)} | {p.get('product_title','<sin titulo>')}")
                print(f"    precio={p.get('target_sale_price') or p.get('sale_price') or p.get('app_sale_price') or 'n/d'} | desc={p.get('discount','n/d')} | rating={p.get('evaluate_rate','n/d')} | ventas={p.get('lastest_volume','n/d')}")
                print("    " + why)

            print("TOP10 >=70:", sum(1 for s,_,_ in ranked[:10] if s>=70),
                  "| TOP10 >=80:", sum(1 for s,_,_ in ranked[:10] if s>=80))

        print()

    print("FIN. La meta es identificar consultas que produzcan candidatos principales >=70 sin falsos positivos.")

if __name__ == "__main__":
    main()
