

from database import init_db, upsert_product, save_price_snapshot, get_history_stats
from scoring import score_offer, classify_offer
from sources.amazon import (
    buscar as buscar_amazon,
    buscar_centro_ofertas,
    get_last_status as get_amazon_status,
)
from sources.aliexpress import (
    buscar as buscar_aliexpress,
    buscar_centro_anuncios,
    get_last_status as get_aliexpress_status,
)
from catalog import iter_queries, query_count
from selection import select_publicable, evaluate_eligibility, _tech_category_title_is_allowed
from dedupe import product_key
import config
import os
import json
from datetime import datetime, timezone
from pathlib import Path

LIMITE_POR_BUSQUEDA = config.MAX_PRODUCTS_PER_QUERY
HEALTH_FILE = Path("data/source_health.json")
_LAST_RUN_HEALTH = {}


def _write_health(payload):
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTH_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(HEALTH_FILE)


def get_last_run_health():
    return dict(_LAST_RUN_HEALTH)


def _classify_amazon(attempted, failed):
    if attempted == 0:
        return "unknown"
    succeeded = attempted - failed
    if succeeded == 0:
        return "unavailable"
    if failed >= 3 or failed / attempted >= 0.5:
        return "degraded"
    return "ok"


def run(return_publicable=False, mode=None):
    global _LAST_RUN_HEALTH
    init_db()
    candidates = []
    stats = {"amazon": 0, "aliexpress": 0}
    mode = mode or os.getenv("SCAN_MODE", "full")
    queries = list(iter_queries(mode))
    print(f"[SCANNER] Modo={mode} | Catálogo tecnológico: {query_count(mode)} consultas")

    amazon_attempted = 0
    amazon_failed = 0
    amazon_consecutive_failures = 0
    amazon_cutoff = False

    for category, q in queries:
        if amazon_consecutive_failures >= 5:
            amazon_cutoff = True
            print("[SCANNER] Amazon: se detienen consultas restantes tras 5 fallos consecutivos.")
            break
        amazon_attempted += 1
        print(f"[SCANNER] Buscando amazon: '{q}' ({category})")
        found = buscar_amazon(q, LIMITE_POR_BUSQUEDA, category=category)
        found = [o for o in found if _tech_category_title_is_allowed(getattr(o, "category", None), getattr(o, "title", ""))]
        candidates.extend(found)
        stats["amazon"] += len(found)
        state = get_amazon_status()
        if state.get("failed"):
            amazon_failed += 1
            amazon_consecutive_failures += 1
        else:
            amazon_consecutive_failures = 0

    # Centro de Ofertas de Amazon: segunda vía de descubrimiento masivo.
    # Busca productos que Amazon está exponiendo explícitamente como ofertas,
    # además del catálogo de consultas normales.
    amazon_deal_found = buscar_centro_ofertas(limite=60)
    amazon_deal_found = [o for o in amazon_deal_found if _tech_category_title_is_allowed(getattr(o, "category", None), getattr(o, "title", ""))]
    candidates.extend(amazon_deal_found)
    stats["amazon"] += len(amazon_deal_found)
    amazon_deal_status = get_amazon_status()
    amazon_attempted += int(amazon_deal_status.get("deal_center_attempted", 0) or 0)
    amazon_failed += int(amazon_deal_status.get("deal_center_failed", 0) or 0)

    aliexpress_attempted = 0
    aliexpress_failed = 0
    aliexpress_api_errors = 0

    for category, q in queries:
        print(f"[SCANNER] Buscando aliexpress: '{q}' ({category})")
        found = buscar_aliexpress(q, LIMITE_POR_BUSQUEDA, category=category)
        found = [o for o in found if _tech_category_title_is_allowed(getattr(o, "category", None), getattr(o, "title", ""))]
        candidates.extend(found)
        stats["aliexpress"] += len(found)
        state = get_aliexpress_status()
        aliexpress_attempted += int(state.get("attempted", 0) or 0)
        aliexpress_failed += int(state.get("failed", 0) or 0)
        aliexpress_api_errors += int(state.get("api_errors", 0) or 0)

    # Centro de Anuncios: fuente adicional de descubrimiento masivo.
    # No sustituye las familias validadas: añade productos de Tendencias que
    # luego pasan por el mismo scoring, histórico, deduplicación y guardas.
    catalog_found = buscar_centro_anuncios(limite=60, channel="tech")
    catalog_found = [o for o in catalog_found if _tech_category_title_is_allowed(getattr(o, "category", None), getattr(o, "title", ""))]
    candidates.extend(catalog_found)
    stats["aliexpress"] += len(catalog_found)
    catalog_state = get_aliexpress_status()
    aliexpress_attempted += int(catalog_state.get("catalog_attempted", 0) or 0)
    aliexpress_failed += int(catalog_state.get("catalog_failed", 0) or 0)
    aliexpress_api_errors += int(catalog_state.get("api_errors", 0) or 0)

    amazon_state = _classify_amazon(amazon_attempted, amazon_failed)
    aliexpress_state = _classify_amazon(aliexpress_attempted, aliexpress_failed)
    health = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "queries_configured": query_count(mode),
        "sources": {
            "amazon": {
                "state": amazon_state,
                "attempted": amazon_attempted,
                "failed": amazon_failed,
                "succeeded": amazon_attempted - amazon_failed,
                "circuit_cutoff": amazon_cutoff,
                "candidates": stats["amazon"],
            },
            "aliexpress": {
                "state": aliexpress_state,
                "attempted": aliexpress_attempted,
                "failed": aliexpress_failed,
                "succeeded": aliexpress_attempted - aliexpress_failed,
                "api_errors": aliexpress_api_errors,
                "candidates": stats["aliexpress"],
            },
        },
    }
    _LAST_RUN_HEALTH = health
    _write_health(health)

    unique = {}
    duplicates = 0
    for offer in candidates:
        key = product_key(offer)
        if key in unique:
            duplicates += 1
            continue
        unique[key] = offer

    scored = []
    for offer in unique.values():
        pid = upsert_product(offer)
        offer.product_id = pid
        # Durante Prime Day no usamos el histórico para informática.
        # La inflación reciente de RAM/SSD y otros componentes puede hacer
        # que un precio actual competitivo parezca caro frente a meses previos.
        ignore_history = os.getenv("TECH_IGNORE_HISTORY", "0").lower() in {"1", "true", "yes", "on"}
        history = {
            "count": 0,
            "average": None,
            "minimum": None,
            "confidence": 0.0,
        } if ignore_history else get_history_stats(pid, 30)
        score, breakdown = score_offer(offer, history)
        classification = classify_offer(score, offer)
        save_price_snapshot(pid, offer.current_price)
        scored.append((score, offer, history, breakdown, classification))

    scored.sort(key=lambda x: x[0], reverse=True)
    publicable = select_publicable(scored)

    print("\n=== RESUMEN DEL ESCANEO ===")
    print(f"Candidatas encontradas: {len(candidates)}")
    print(f"  Amazon:              {stats['amazon']}")
    print(f"  AliExpress:           {stats['aliexpress']}")
    print(f"Duplicadas:             {duplicates}")
    print(f"Válidas:                {len(scored)}")
    print(f"Publicables por reglas: {len(publicable)}")
    print(f"Salud Amazon:          {amazon_state}")

    print("\n=== TOP OFERTAS DETECTADAS ===")
    if not scored:
        print("No se han encontrado ofertas.")

    for i, (score, offer, history, b, classification) in enumerate(scored[:20], 1):
        d = offer.discount_pct
        dstr = f"-{d:.1f}%" if d is not None else "n/d"
        avg = f"{history['average']:.2f} €" if history["average"] is not None else "n/d"
        mn = f"{history['minimum']:.2f} €" if history["minimum"] is not None else "n/d"
        rating = f"{offer.rating:.1f}" if offer.rating is not None else "n/d"
        reviews = f"{offer.reviews:,}" if offer.reviews is not None else "n/d"
        print(f"{i:02d}. [{score:05.2f}] {classification:<14} {offer.source:<10} {offer.category or '-':<14} {offer.title[:70]}")
        print(f"    Precio: {offer.current_price:.2f} € | Referencia: {offer.reference_price:.2f} € | {dstr}")
        print(f"    Histórico: {history['count']} muestras | media30={avg} | mínimo30={mn}")
        print(f"    Calidad: rating={rating}/5 | reseñas={reviews}")
        print(f"    Deal Score: {b['deal_score']:.1f} | Trust Score: {b['trust_score']:.1f} | Confianza: {b['confidence_factor']:.2f} | Publicación: {score:.1f}")
        decision = evaluate_eligibility(offer, score, classification)
        if decision.reasons:
            print(f"    Filtro: NO elegible ({', '.join(decision.reasons)})")
        else:
            print("    Filtro: ELEGIBLE")

    print("\n=== TOP PUBLICABLE (diversidad + máx. 2 por categoría) ===")
    if not publicable:
        print("No hay candidatos publicables con las reglas actuales.")
    for i, (score, offer, history, b, classification) in enumerate(publicable, 1):
        print(f"{i:02d}. [{score:05.2f}] {classification:<14} {offer.category or '-':<14} {offer.title[:75]}")
        print(f"    Precio: {offer.current_price:.2f} € | Referencia: {offer.reference_price:.2f} € | Descuento: {offer.discount_pct:.1f}%")
        print(f"    Calidad: rating={offer.rating if offer.rating is not None else 'n/d'} | reseñas={offer.reviews if offer.reviews is not None else 'n/d'}")
    return (scored, publicable) if return_publicable else scored


if __name__ == "__main__":
    run()


