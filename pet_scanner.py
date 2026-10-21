from __future__ import annotations

from dedupe import product_key
from database import init_db, upsert_product, save_price_snapshot, get_history_stats
from scoring import score_offer, classify_offer
from sources.amazon import buscar as buscar_amazon
from sources.aliexpress import buscar as buscar_aliexpress
from pet_channel import select_pet_publicable
import config

QUERIES = {
    "dog": ("comida perro", "premios perro", "galletas perro", "snacks dentales perro"),
    "cat": ("comida gato", "churu gato", "snacks cremosos gato", "galletas gato"),
    "pet_care": ("cepillo mascota", "fuente agua mascota"),
    "pet_accessories": ("correa perro", "transportin mascota"),
    "aquarium": ("acuario", "filtro acuario"),
}


def scan():
    init_db()
    candidates = []

    for category, queries in QUERIES.items():
        for q in queries:
            try:
                candidates.extend(
                    buscar_amazon(q, config.MAX_PRODUCTS_PER_QUERY, category=category)                )
            except Exception as exc:
                print(f"[PET-SCANNER] Amazon '{q}': {type(exc).__name__}: {exc}")
            try:
                candidates.extend(
                    buscar_aliexpress(q, config.MAX_PRODUCTS_PER_QUERY, category=category)
                )
            except Exception as exc:
                print(f"[PET-SCANNER] AliExpress '{q}': {type(exc).__name__}: {exc}")

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
        score, breakdown = score_offer(offer, history)
        classification = classify_offer(score, offer)
        save_price_snapshot(product_id, offer.current_price)
        scored.append((score, offer, history, breakdown, classification))

    publicable = select_pet_publicable(scored)
    print(        f"[PET-SCANNER] candidatas={len(candidates)} "
        f"unicas={len(unique)} publicables={len(publicable)}"
    )
    for i, row in enumerate(publicable, 1):
        score, offer, history, breakdown, classification = row
        print(
            f"{i:02d}. [{offer.category}] [{score:.1f}] "
            f"{offer.source}:{offer.external_id} {offer.title[:90]}"
        )
    return scored, publicable


if __name__ == "__main__":
    scan()