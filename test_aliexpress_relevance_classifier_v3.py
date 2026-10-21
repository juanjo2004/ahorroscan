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
PARTNER_ID = "iop44-sdk-typescript-20231021"
METHOD = "aliexpress.affiliate.product.query"


@dataclass(frozen=True)
class Rule:
    query: str
    core_any: tuple[str, ...]
    must_groups: tuple[tuple[str, ...], ...]
    positive: tuple[str, ...]
    hard_negative: tuple[str, ...]
    soft_negative: tuple[str, ...]


RULES = (
    Rule(
        "raton gaming",
        ("raton", "ratón", "mouse"),
        (("gaming", "juegos", "gamer"),),
        ("inalámbrico", "inalambrico", "wireless", "bluetooth", "2.4g",
         "sensor", "dpi", "optico", "óptico", "rgb", "ergonomico", "ergonómico",
         "polling", "16000", "26000", "3200dpi"),
        ("patines", "skates", "feet", "pies de repuesto", "pies para ratón",
         "grip", "agarre", "cinta de agarre", "cable de carga", "cable de datos",
         "microinterruptor", "switch de ratón", "switch para ratón", "encoder",
         "codificador", "repuesto", "replacement", "estuche", "funda",
         "alfombrilla", "almohadilla", "case", "adaptador", "adaptadores",
         "pegatina", "pegatinas", "piezas"),
        ("accesorio", "accesorios", "pieza", "piezas"),
    ),
    Rule(
        "ssd nvme",
        ("ssd", "nvme", "unidad de estado sólido", "unidad de estado solido"),
        (("m.2", "m 2"),),
        ("pcie", "pci-e", "gen4", "gen5", "1tb", "2tb", "4tb", "500gb",
         "256gb", "512gb", "128gb", "dram", "tlc", "qlc", "nand",
         "read", "write", "mb/s", "7000", "10000", "12000", "14000"),
        ("disipador", "disipador de calor", "heatsink", "cooler", "refrigerador",
         "mini pc", "laptop", "notebook", "portátil", "portatil", "carcasa",
         "enclosure", "case", "adaptador", "adapter", "conmutador", "switch",
         "soporte", "base", "dock", "estuche", "cable", "cables"),
        ("externo", "external", "usb", "almacenamiento externo"),
    ),
    Rule(
        "memoria ram ddr5",
        ("memoria ram", "ram"),
        (("ddr5",),),
        ("udimm", "dimm", "288pin", "xmp", "expo", "4800", "5200", "5600",
         "6000", "6200", "6400", "6800", "7200", "pc5", "desktop", "escritorio"),
        ("ddr4", "ddr3", "ddr2", "sodimm", "so-dimm", "portátil", "portatil",
         "laptop", "notebook", "adaptador", "adapter", "plantilla",
         "reballing", "stencil", "memoria para laptop"),
        ("disipador", "heatsink", "radiador"),
    ),
    Rule(
        "monitor 4k",
        ("monitor", "pantalla", "display"),
        (("4k", "uhd"),),
        ("27", "24", "25", "32", "34", "43", "144hz", "165hz", "180hz",
         "240hz", "120hz", "hdmi", "displayport", "ips", "va", "oled",
         "led", "vrr", "freesync", "g-sync", "gsync", "1ms"),
        ("cámara", "camara", "dashcam", "coche", "lente", "lens", "gafas",
         "smart glasses", "proyector", "extensor hdmi", "adaptador hdmi",
         "capturadora", "video transmitter", "transmisor de video"),
        ("soporte", "base", "cable", "adaptador", "accesorio"),
    ),
    Rule(
        "teclado mecanico",
        ("teclado", "keyboard"),
        (("mecánico", "mecanico", "mechanical"),),
        ("hot-swap", "hotswap", "qmk", "via", "rgb", "bluetooth", "wireless",
         "2.4g", "pbt", "87 teclas", "104 teclas", "108 teclas", "75%",
         "65%", "60%", "tkl", "layout", "ansi", "iso", "switch"),
        ("alfombrilla", "mouse pad", "pegatina", "sticker", "estuche", "funda",
         "soporte", "stand", "mesa", "organizador", "llavero", "juguete",
         "keycap suelta", "keycaps sueltos", "tecla suelta", "switch suelto",
         "switches sueltos", "repuesto"),
        ("accesorio", "accesorios"),
    ),
)


def norm(s: str) -> str:
    s = (s or "").lower()
    table = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"})
    s = s.translate(table)
    return " ".join(s.split())


def sign(params: dict[str, str]) -> str:
    canonical = "".join(k + str(params[k]) for k in sorted(params) if params[k] not in (None, ""))
    return hmac.new(str(ALI_APP_SECRET).encode(), canonical.encode(), hashlib.sha256).hexdigest().upper()


def fetch(keyword: str) -> list[dict]:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Falta data/aliexpress_token.json")
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    if not token:
        raise RuntimeError("Falta access_token")

    p = {
        "app_key": str(ALI_APP_KEY),
        "session": token,
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
    p["sign"] = sign(p)
    r = requests.post(ENDPOINT, data=p, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"})
    r.raise_for_status()
    data = r.json()
    rr = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products = result.get("products", {}).get("product", []) if isinstance(result, dict) else []
    return products if isinstance(products, list) else []


def contains_any(text: str, terms: tuple[str, ...] | list[str]) -> list[str]:
    return [t for t in terms if norm(t) in text]


def score_product(p: dict, rule: Rule) -> tuple[int, list[str]]:
    title = norm(str(p.get("product_title", "")))
    cat = norm(f"{p.get('first_level_category_name','')} {p.get('second_level_category_name','')}")

    score = 0
    reasons = []

    core = contains_any(title, rule.core_any)
    if core:
        score += 30
        reasons.append("core:" + ",".join(core[:4]))
    else:
        reasons.append("sin_core")
        return 0, reasons

    missing = []
    for group in rule.must_groups:
        if contains_any(title, group):
            score += 20
            reasons.append("must:" + ",".join(contains_any(title, group)[:3]))
        else:
            missing.append("/".join(group))
    if missing:
        score -= 10
        reasons.append("falta_must:" + ";".join(missing))

    pos = contains_any(title, rule.positive)
    score += min(30, 5 * len(pos))
    if pos:
        reasons.append("positivos:" + ",".join(pos[:8]))

    hard = contains_any(title, rule.hard_negative)
    if hard:
        # Product accessories/replacements are fatal for this project.
        score -= min(80, 55 + 10 * (len(hard) - 1))
        reasons.append("negativos_fuertes:" + ",".join(hard[:8]))

    soft = contains_any(title, rule.soft_negative)
    if soft:
        score -= min(15, 7 * len(soft))
        reasons.append("negativos_suaves:" + ",".join(soft[:5]))

    if any(x in cat for x in ("perifericos", "componentes de ordenadores", "monitores", "pantallas")):
        score += 10
        reasons.append("categoria_favorable")

    # Category-specific sanity caps.
    if rule.query == "raton gaming":
        # A real mouse should not be scoreable above "dudoso" if it only says mouse
        # and gaming but has no hardware/usage signal.
        if not pos:
            score = min(score, 45)
        if hard:
            score = min(score, 15)

    elif rule.query == "ssd nvme":
        if any(x in title for x in ("disipador", "heatsink", "cooler")):
            score = min(score, 20)
        if any(x in title for x in ("mini pc", "laptop", "notebook", "portatil", "portátil", "carcasa", "enclosure")):
            score = min(score, 10)
        if ("ssd" in title or "nvme" in title) and any(x in title for x in ("tb", "gb")):
            score += 10
        if "m.2" in title and ("ssd" in title or "nvme" in title):
            score += 10

    elif rule.query == "memoria ram ddr5":
        if any(x in title for x in ("ddr4", "ddr3", "sodimm", "so-dimm")):
            score = min(score, 10)
        if "desktop" in title or "escritorio" in title or "udimm" in title:
            score += 10

    elif rule.query == "monitor 4k":
        if "monitor" not in title and "pantalla" not in title and "display" not in title:
            return 0, reasons + ["sin_tipo_monitor"]
        if any(x in title for x in ("cámara", "camara", "gafas", "proyector", "dashcam")):
            score = min(score, 5)

    elif rule.query == "teclado mecanico":
        if "teclado" not in title and "keyboard" not in title:
            return 0, reasons + ["sin_tipo_teclado"]
        if any(x in title for x in ("llavero", "juguete")):
            score = min(score, 10)

    return max(0, min(100, score)), reasons


def label(score: int) -> str:
    if score >= 80:
        return "MUY RELEVANTE"
    if score >= 70:
        return "RELEVANTE"
    if score >= 55:
        return "DUDOSO"
    return "NO RELEVANTE"


def main() -> int:
    print("ALIEXPRESS - CLASIFICADOR V3")
    print("Objetivo: separar producto principal de accesorios/repuestos con reglas por categoria.")
    print("No modifica SQLite, scanner ni Telegram.\n")

    for rule in RULES:
        print(f"=== {rule.query} ===")
        try:
            products = fetch(rule.query)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}\n")
            continue

        ranked = []
        for p in products:
            s, reasons = score_product(p, rule)
            ranked.append((s, p, reasons))
        ranked.sort(key=lambda x: x[0], reverse=True)

        for i, (s, p, reasons) in enumerate(ranked, 1):
            print(f"{i:02d}. [{s:3d}] {label(s)} | {p.get('product_title','<sin titulo>')}")
            print(
                f"    precio={p.get('target_sale_price') or p.get('sale_price') or p.get('app_sale_price') or 'n/d'}"
                f" | desc={p.get('discount','n/d')} | rating={p.get('evaluate_rate','n/d')}"
                f" | ventas={p.get('lastest_volume','n/d')}"
            )
            print("    razones=" + "; ".join(reasons))
        counts = {lab: sum(label(s) == lab for s, _, _ in ranked)
                  for lab in ("MUY RELEVANTE", "RELEVANTE", "DUDOSO", "NO RELEVANTE")}
        print("Resumen:", ", ".join(f"{k}={v}" for k, v in counts.items()))
        print()

    print("FIN. La regla de publicación NO se decide aquí; primero calibramos relevancia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
