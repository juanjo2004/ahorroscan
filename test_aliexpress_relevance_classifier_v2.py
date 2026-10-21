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
    strong_terms: tuple[str, ...]
    support_groups: tuple[tuple[str, ...], ...]
    bonus_terms: tuple[str, ...]
    hard_negative: tuple[str, ...]
    soft_negative: tuple[str, ...]


RULES = (
    Rule(
        query="raton gaming",
        strong_terms=("raton", "ratón", "mouse"),
        support_groups=(("gaming", "juegos"), ("inalámbrico", "inalambrico", "wireless")),
        bonus_terms=("optico", "óptico", "sensor", "dpi", "2.4g", "bluetooth", "rgb", "ergonomico", "ergonómico"),
        hard_negative=("patines", "skates", "feet", "pies de repuesto", "grip", "agarre",
                       "cable de carga", "cable de datos", "microinterruptor", "switch",
                       "encoder", "repuesto", "replacement", "estuche", "funda", "alfombrilla",
                       "almohadilla", "case", "adaptador"),
        soft_negative=("cinta", "pegatina", "pegatinas", "accesorio", "pieza"),
    ),
    Rule(
        query="ssd nvme",
        strong_terms=("ssd", "nvme", "unidad de estado sólido", "unidad de estado solido"),
        support_groups=(("m.2", "m 2"), ("pcie", "pci-e", "nvme")),
        bonus_terms=("1tb", "2tb", "4tb", "500gb", "gen4", "gen5", "7000mb/s", "10000mb/s", "14000mb/s"),
        hard_negative=("mini pc", "laptop", "notebook", "portátil", "portatil", "carcasa",
                       "enclosure", "case", "adaptador", "adapter", "cable", "conmutador",
                       "switch", "soporte", "base", "dock", "estuche"),
        soft_negative=("externo", "external", "usb"),
    ),
    Rule(
        query="memoria ram ddr5",
        strong_terms=("memoria ram", "ram"),
        support_groups=(("ddr5",),),
        bonus_terms=("udimm", "dimm", "288pin", "xmp", "expo", "4800", "5200", "5600", "6000", "6400"),
        hard_negative=("ddr4", "ddr3", "ddr2", "sodimm", "so-dimm", "portátil", "portatil",
                       "laptop", "notebook", "adaptador", "adapter", "plantilla", "reballing"),
        soft_negative=("disipador", "heatsink"),
    ),
    Rule(
        query="monitor 4k",
        strong_terms=("monitor", "pantalla", "display"),
        support_groups=(("4k", "uhd"),),
        bonus_terms=("27", "24", "32", "144hz", "165hz", "240hz", "hdmi", "displayport", "ips", "va", "oled"),
        hard_negative=("cámara", "camara", "dashcam", "coche", "lente", "lens", "gafas", "smart glasses",
                       "proyector", "proyector", "extensor hdmi", "adaptador hdmi"),
        soft_negative=("soporte", "carcasa", "accesorio", "cable"),
    ),
    Rule(
        query="teclado mecanico",
        strong_terms=("teclado", "keyboard"),
        support_groups=(("mecánico", "mecanico", "mechanical"),),
        bonus_terms=("switch", "hot-swap", "hotswap", "rgb", "qmk", "via", "bluetooth", "2.4g",
                     "pbt", "87 teclas", "104 teclas", "108 teclas", "75%", "65%", "60%"),
        hard_negative=("alfombrilla", "mouse pad", "pegatina", "sticker", "estuche", "funda",
                       "soporte", "stand", "mesa", "organizador", "keycap suelta", "tecla suelta",
                       "switch suelto", "repuesto"),
        soft_negative=("keycap", "keycaps", "switches"),
    ),
)


def norm(s: str) -> str:
    s = (s or "").lower()
    trans = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"})
    s = s.translate(trans)
    return " ".join(s.split())


def sign(params: dict[str, str]) -> str:
    canonical = "".join(k + str(params[k]) for k in sorted(params) if params[k] not in (None, ""))
    return hmac.new(
        str(ALI_APP_SECRET).encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest().upper()


def fetch(keyword: str) -> list[dict]:
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    if not token:
        raise RuntimeError("Falta access_token en data/aliexpress_token.json")

    params = {
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
    params["sign"] = sign(params)

    r = requests.post(
        ENDPOINT,
        data=params,
        timeout=30,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    r.raise_for_status()
    data = r.json()
    rr = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
    result = rr.get("result", {}) if isinstance(rr, dict) else {}
    products = result.get("products", {}).get("product", []) if isinstance(result, dict) else []
    return products if isinstance(products, list) else []


def score_product(p: dict, rule: Rule) -> tuple[int, list[str]]:
    title = norm(str(p.get("product_title", "")))
    cat = norm(f"{p.get('first_level_category_name', '')} {p.get('second_level_category_name', '')}")

    score = 0
    reasons: list[str] = []

    # Must contain a product-type core term.
    if any(norm(t) in title for t in rule.strong_terms):
        score += 35
        reasons.append("termino_principal")
    else:
        score -= 35
        reasons.append("falta_termino_principal")

    # Each support group contributes when at least one member appears.
    for group in rule.support_groups:
        if any(norm(t) in title for t in group):
            score += 15
            reasons.append("grupo:" + "/".join(group))

    # Specs / characteristic terms.
    bonus_hits = [t for t in rule.bonus_terms if norm(t) in title]
    score += min(20, 5 * len(bonus_hits))
    if bonus_hits:
        reasons.append("bonus:" + ",".join(bonus_hits[:6]))

    hard_hits = [t for t in rule.hard_negative if norm(t) in title]
    if hard_hits:
        score -= min(65, 35 + 10 * (len(hard_hits) - 1))
        reasons.append("negativo_fuerte:" + ",".join(hard_hits[:6]))

    soft_hits = [t for t in rule.soft_negative if norm(t) in title]
    if soft_hits:
        score -= min(20, 7 * len(soft_hits))
        reasons.append("negativo_suave:" + ",".join(soft_hits[:6]))

    # Category is supportive only, never mandatory.
    if any(x in cat for x in ("perifericos", "componentes de ordenadores", "monitores", "pantallas")):
        score += 10
        reasons.append("categoria_favorable")

    # Minimum sanity rules prevent obvious type mismatches.
    if rule.query == "ssd nvme" and any(x in title for x in ("mini pc", "laptop", "notebook", "portatil", "portátil")):
        score = min(score, 15)
    if rule.query == "monitor 4k" and not any(x in title for x in ("monitor", "pantalla", "display")):
        score = min(score, 20)
    if rule.query == "teclado mecanico" and "teclado" not in title and "keyboard" not in title:
        score = min(score, 20)

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
    if not (ALI_APP_KEY and ALI_APP_SECRET and ALI_TRACKING_ID):
        print("ERROR: faltan credenciales de AliExpress en .env")
        return 2
    if not TOKEN_FILE.exists():
        print("ERROR: falta data/aliexpress_token.json")
        return 3

    print("ALIEXPRESS - CLASIFICADOR V2")
    print("Score 0-100. La categoria es señal de apoyo, no requisito.")
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
            title = p.get("product_title", "<sin titulo>")
            price = p.get("target_sale_price") or p.get("sale_price") or p.get("app_sale_price") or "n/d"
            print(f"{i:02d}. [{s:3d}] {label(s)} | {title}")
            print(f"    precio={price} | desc={p.get('discount','n/d')} | rating={p.get('evaluate_rate','n/d')} | ventas={p.get('lastest_volume','n/d')}")
            print(f"    razones={'; '.join(reasons)}")

        counts = {lab: sum(label(s) == lab for s, _, _ in ranked)
                  for lab in ("MUY RELEVANTE", "RELEVANTE", "DUDOSO", "NO RELEVANTE")}
        print("Resumen:", ", ".join(f"{k}={v}" for k, v in counts.items()))
        print()

    print("FIN. Umbral candidato para el siguiente paso: >=70, pendiente de calibración con resultados reales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
