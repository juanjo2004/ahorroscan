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
    Rule(
        "raton_gaming",
        ("raton gaming inalambrico", "wireless gaming mouse"),
        {"raton gaming inalambrico": 12, "wireless gaming mouse": 10},
        ("raton", "ratón", "mouse"),
        (("gaming", "gamer", "juegos"),),
        ("inalambrico", "inalámbrico", "wireless", "bluetooth", "2.4g", "sensor",
         "dpi", "optico", "óptico", "rgb", "ergonomico", "ergonómico", "paw3395",
         "polling", "26000dpi", "8k"),
        ("patines", "skates", "feet", "pies de repuesto", "grip", "agarre",
         "cinta de agarre", "cable de carga", "cable de datos", "microinterruptor",
         "encoder", "codificador", "repuesto", "replacement", "estuche", "funda",
         "alfombrilla", "almohadilla", "case", "adaptador", "adaptadores",
         "pegatina", "pegatinas", "pieza", "piezas", "dongle", "receptor usb"),
        ("accesorio", "accesorios"),
    ),
    Rule(
        "ssd_nvme",
        ("m2 nvme ssd 1tb", "pcie 4.0 nvme ssd", "ssd nvme 1tb m2"),
        {"m2 nvme ssd 1tb": 15, "pcie 4.0 nvme ssd": 15, "ssd nvme 1tb m2": 12},
        ("ssd", "nvme", "unidad de estado sólido", "unidad de estado solido"),
        (),
        ("m.2", "m 2", "pcie", "pci-e", "gen3", "gen4", "gen5", "2280",
         "1tb", "2tb", "4tb", "500gb", "512gb", "256gb", "mb/s",
         "7400", "7000", "10000", "14000", "interno", "interna"),
        ("disipador", "disipador de calor", "heatsink", "cooler", "radiador",
         "mini pc", "carcasa", "enclosure", "case", "adaptador", "adapter",
         "conmutador", "switch", "soporte", "base", "dock", "estuche",
         "cable", "cables", "externo", "external", "almacenamiento externo"),
        ("usb",),
    ),
    Rule(
        "monitor_4k",
        ("monitor 4k 27 pulgadas", "uhd monitor 27"),
        {"monitor 4k 27 pulgadas": 15, "uhd monitor 27": 15},
        ("monitor", "pantalla", "display"),
        (("4k", "uhd"),),
        ("27", "24", "25", "32", "34", "144hz", "165hz", "180hz", "240hz",
         "120hz", "hdmi", "displayport", "ips", "va", "oled", "freesync",
         "g-sync", "g sync", "hdr", "vesa", "3840x2160", "60hz"),
        ("cámara", "camara", "dashcam", "coche", "lente", "lens", "gafas",
         "smart glasses", "proyector", "extensor hdmi", "adaptador hdmi",
         "capturadora", "transmisor", "transmisión", "cable",
         "fuente de alimentación", "panel de repuesto", "pantalla de repuesto",
         "controladora", "placa controladora"),
        ("accesorio", "accesorios"),
    ),
    Rule(
        "teclado_mecanico",
        ("75 percent mechanical keyboard", "teclado gaming mecanico"),
        {"75 percent mechanical keyboard": 18, "teclado gaming mecanico": 10},
        ("teclado", "keyboard"),
        (("mecanico", "mecánico", "mechanical"),),
        ("hot-swap", "hotswap", "qmk", "via", "rgb", "bluetooth", "wireless",
         "2.4g", "pbt", "87 teclas", "104 teclas", "108 teclas", "75%",
         "65%", "60%", "tkl", "layout", "ansi", "iso"),
        ("alfombrilla", "mouse pad", "pegatina", "sticker", "estuche", "funda",
         "soporte", "stand", "mesa", "organizador", "llavero", "juguete",
         "keycap", "keycaps", "tecla suelta", "teclas sueltas", "teclas",
         "juego de teclas", "switches", "interruptores", "cable de teclado",
         "placa de posicionamiento", "repuesto", "cosplay", "figura"),
        ("accesorio", "accesorios"),
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
        raise RuntimeError("Falta access_token")

    params = {
        "app_key": str(ALI_APP_KEY), "session": token, "format": "json",
        "method": METHOD, "partner_id": PARTNER_ID, "sign_method": "sha256",
        "simplify": "false", "timestamp": str(int(time.time() * 1000)),
        "v": "2.0", "keywords": keyword, "page_no": "1", "page_size": "20",
        "tracking_id": str(ALI_TRACKING_ID), "target_currency": "EUR",
        "target_language": "ES", "ship_to_country": "ES",
    }
    params["sign"] = sign(params)

    r = requests.post(ENDPOINT, data=params, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"})
    r.raise_for_status()
    data = r.json()
    rr = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products = result.get("products", {}).get("product", []) if isinstance(result, dict) else []
    return products if isinstance(products, list) else []


def score_product(p: dict, rule: Rule, query: str) -> tuple[int, list[str]]:
    title = norm(str(p.get("product_title", "")))
    cat = norm(f"{p.get('first_level_category_name','')} {p.get('second_level_category_name','')}")
    reasons = []

    if not any(norm(x) in title for x in rule.core):
        return 0, ["sin_core"]

    score = 35
    reasons.append("producto_principal")

    qboost = rule.query_boost.get(query, 0)
    score += qboost
    if qboost:
        reasons.append(f"consulta_especifica+{qboost}")

    missing = []
    for group in rule.required:
        if any(norm(x) in title for x in group):
            score += 15
            reasons.append("requisito:" + "/".join(group))
        else:
            missing.append("/".join(group))
    if missing:
        score -= 15
        reasons.append("falta:" + ";".join(missing))

    pos = [x for x in rule.positive if norm(x) in title]
    score += min(25, 5 * len(pos))
    if pos:
        reasons.append("positivos:" + ",".join(pos[:8]))

    neg = [x for x in rule.hard_negative if norm(x) in title]
    if neg:
        score -= min(90, 70 + 8 * (len(neg) - 1))
        reasons.append("bloqueos:" + ",".join(neg[:8]))

    soft = [x for x in rule.soft_negative if norm(x) in title]
    if soft:
        score -= min(15, 7 * len(soft))
        reasons.append("avisos:" + ",".join(soft[:5]))

    if any(x in cat for x in ("perifericos", "componentes de ordenadores", "monitores")):
        score += 10
        reasons.append("categoria_util")

    # Category-specific hard sanity:
    if rule.name == "ssd_nvme":
        # Laptop compatibility is normal for an internal SSD and is NOT negative.
        if any(x in title for x in ("mini pc", "carcasa", "enclosure", "adaptador", "conmutador",
                                     "disipador", "soporte", "dock", "externo", "external", "usb")):
            score = min(score, 10)
        if not any(x in title for x in ("tb", "gb")):
            score = min(score, 45)

    elif rule.name == "monitor_4k":
        if not any(x in title for x in ("monitor", "pantalla", "display")):
            return 0, reasons + ["sin_tipo_monitor"]
        if not any(x in title for x in ("4k", "uhd")):
            score = min(score, 50)

    elif rule.name == "teclado_mecanico":
        if not any(x in title for x in ("teclado", "keyboard")):
            return 0, reasons + ["sin_tipo_teclado"]
        if any(x in title for x in ("teclas", "keycap", "keycaps", "juego de teclas", "switches", "interruptores")):
            score = min(score, 15)

    return max(0, min(100, score)), reasons


def label(s: int) -> str:
    if s >= 80:
        return "MUY RELEVANTE"
    if s >= 70:
        return "RELEVANTE"
    if s >= 55:
        return "DUDOSO"
    return "NO RELEVANTE"


def main():
    print("ALIEXPRESS - QUERY + CLASSIFIER V5")
    print("Prueba final de consultas ganadoras + bloqueo explícito de accesorios.")
    print("No modifica SQLite, scanner, histórico ni Telegram.\n")

    for rule in RULES:
        print(f"===== {rule.name} =====")
        for q in rule.queries:
            try:
                products = fetch(q)
            except Exception as exc:
                print(f"\nQUERY: {q}\nERROR: {type(exc).__name__}: {exc}")
                continue

            ranked = []
            for p in products:
                s, why = score_product(p, rule, q)
                ranked.append((s, p, why))
            ranked.sort(key=lambda x: x[0], reverse=True)

            print(f"\nQUERY: {q} | resultados={len(ranked)}")
            for i, (s, p, why) in enumerate(ranked[:10], 1):
                print(f"{i:02d}. [{s:3d}] {label(s)} | {p.get('product_title','<sin titulo>')}")
                print(f"    precio={p.get('target_sale_price') or p.get('sale_price') or p.get('app_sale_price') or 'n/d'} | desc={p.get('discount','n/d')} | rating={p.get('evaluate_rate','n/d')} | ventas={p.get('lastest_volume','n/d')}")
                print("    " + ";".join(why))
            print(
                "TOP10 >=70:", sum(1 for s, _, _ in ranked[:10] if s >= 70),
                "| TOP10 >=80:", sum(1 for s, _, _ in ranked[:10] if s >= 80)
            )
        print()

    print("FIN. Si las consultas ganadoras mantienen candidatos limpios, el siguiente paso será integrar el motor en scanner.py.")

if __name__ == "__main__":
    main()
