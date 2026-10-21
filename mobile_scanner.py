from __future__ import annotations

from dedupe import product_key
from database import init_db, upsert_product, save_price_snapshot, get_history_stats
from scoring import score_offer, classify_offer
from sources.amazon import buscar as buscar_amazon, get_last_status as amazon_last_status
from sources.aliexpress import buscar as buscar_aliexpress
from mobile_channel import select_mobile_publicable
from prime_day import history_for
import config


PHONE_QUERIES = (
    # Keep each query aligned with the AliExpress discovery allowlist.
    "movil 5g",
    "telefonos moviles",
    "telefonos moviles 5g",
    "xiaomi movil",
    "redmi smartphone",
    "poco smartphone",
    "samsung galaxy",
    "smartphone 5g",
    "smartphone 4g",
    "samsung galaxy",
    "xiaomi redmi poco",
    "iphone",
    "google pixel",
    "motorola smartphone",
    "honor smartphone",
    "oppo realme",
    "oneplus nothing phone",
    "vivo smartphone",
)

ACCESSORY_QUERIES = (
    "cargador movil",
    "cargador usb c",
    "funda movil",
    "protector pantalla movil",
)

MOBILE_MAX_PRODUCTS_PER_QUERY = 15


def scan():
    init_db()
    candidates = []

    amazon_circuit_open = False
    for q in PHONE_QUERIES:
        try:
            candidates.extend(
                buscar_amazon(q, MOBILE_MAX_PRODUCTS_PER_QUERY, category="smartphones")
            )
        except Exception as exc:
            print(f"[MOBILE-SCANNER] Amazon '{q}': {type(exc).__name__}: {exc}")
        status = amazon_last_status()
        reason = str(status.get("reason") or "").lower()
        if status.get("failed"):
            amazon_circuit_open = True
            print(
                "[MOBILE-SCANNER] Circuito Amazon abierto para este ciclo "
                f"(consulta='{q}', motivo={reason or 'fallo_transitorio'}); "
                "se omiten más búsquedas Amazon para no agravar el bloqueo."
            )
            break

    # AliExpress expands this validated category into its full query bank.
    # Calling it once per Amazon query would repeat that bank up to 12 times.
    try:
        candidates.extend(
            buscar_aliexpress("telefonos moviles", MOBILE_MAX_PRODUCTS_PER_QUERY, category="smartphones")
        )
    except Exception as exc:
        print(f"[MOBILE-SCANNER] AliExpress smartphones: {type(exc).__name__}: {exc}")

    for q in ACCESSORY_QUERIES:
        if not amazon_circuit_open:
            try:
                candidates.extend(
                    buscar_amazon(q, config.MAX_PRODUCTS_PER_QUERY, category="mobile_accessories")
                )
            except Exception as exc:
                print(f"[MOBILE-SCANNER] Amazon accesorio '{q}': {type(exc).__name__}: {exc}")
            status = amazon_last_status()
            reason = str(status.get("reason") or "").lower()
            if status.get("failed"):
                amazon_circuit_open = True
                print(
                    "[MOBILE-SCANNER] Circuito Amazon abierto durante accesorios "
                    f"(consulta='{q}', motivo={reason or 'fallo_transitorio'}); "
                    "se omiten más búsquedas Amazon para este ciclo."
                )

    unique = {}
    for offer in candidates:
        key = product_key(offer)
        if key not in unique:
            unique[key] = offer

    scored = []
    for offer in unique.values():
        product_id = upsert_product(offer)
        offer.product_id = product_id
        history = get_history_stats(product_id, 30)
        history = history_for(history)
        score, breakdown = score_offer(offer, history)
        classification = classify_offer(score, offer)
        save_price_snapshot(product_id, offer.current_price)
        scored.append((score, offer, history, breakdown, classification))

    publicable = select_mobile_publicable(scored)

    print(
        f"[MOBILE-SCANNER] candidatas={len(candidates)} "
        f"unicas={len(unique)} publicables={len(publicable)}"
    )
    for i, row in enumerate(publicable, 1):
        score, offer, history, breakdown, classification = row
        kind = "smartphone" if offer.category == "smartphones" else "accesorio"
        print(
            f"{i:02d}. [{kind}] [{score:.1f}] "
            f"{offer.source}:{offer.external_id} {offer.title[:90]}"
        )

    return scored, publicable


if __name__ == "__main__":
    scan()