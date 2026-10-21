"""Motor de tendencias para AhorroScan Tech."""
from __future__ import annotations
import json, math, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from catalog import CATALOG, DISCOVERY_CATALOG
from sources.aliexpress import buscar_centro_anuncios
from sources.amazon import buscar_centro_ofertas

OUT = Path("data/trends_tech.json")
MAX_EXTRA_CATEGORIES = 5
# Categorías estratégicas que no queremos que desaparezcan del radar aunque
# una lectura puntual de tendencias las coloque por debajo del top.
CORE_CATEGORIES = {"smartphones", "monitors", "audio"}
FRESH_HOURS = 12


def _ali_signal(items):
    by = defaultdict(list)
    for item in items:
        cat = item.category
        if not cat: continue
        volume = max(0, int(item.reviews or 0))
        rating = float(item.rating or 0)
        discount = float(item.discount_pct or 0)
        signal = math.log1p(volume) * (0.75 + min(discount, 70) / 100) * (0.75 + min(rating, 5) / 5)
        by[cat].append(signal)
    return by


def _amazon_signal(items):
    by = defaultdict(list)
    for item in items:
        cat = item.category
        if not cat: continue
        reviews = max(0, int(item.reviews or 0))
        rating = float(item.rating or 0)
        discount = float(item.discount_pct or 0)
        signal = 1.0 + math.log1p(reviews) * 0.20 + min(discount, 70) / 100 + rating / 10
        by[cat].append(signal)
    return by


def update() -> dict:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ali = buscar_centro_anuncios(limite=100, channel="tech")
    amazon = buscar_centro_ofertas(limite=60)
    a, z = _ali_signal(ali), _amazon_signal(amazon)
    rows = []
    for cat in DISCOVERY_CATALOG:
        av, zv = a.get(cat, []), z.get(cat, [])
        ali_score = sum(sorted(av, reverse=True)[:5])
        amazon_score = sum(sorted(zv, reverse=True)[:5])
        rows.append((cat, ali_score + amazon_score * 0.45, len(av), len(zv)))
    max_raw = max((x[1] for x in rows), default=1.0) or 1.0
    normalized = [{"category": c, "score": round(raw / max_raw * 100, 2), "ali_candidates": na, "amazon_candidates": nz} for c, raw, na, nz in rows]
    normalized.sort(key=lambda x: x["score"], reverse=True)
    payload = {
        "generated_at": time.time(),
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
        "source": "aliexpress_center_volume+amazon_deals",
        "categories": normalized,
        "top_categories": [x["category"] for x in normalized[:MAX_EXTRA_CATEGORIES]],
        "core_categories": sorted(CORE_CATEGORIES),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[TRENDS] Top:", ", ".join(f"{x['category']}={x['score']:.1f}" for x in normalized[:8]))
    return payload


def load() -> dict:
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        if time.time() - float(data.get("generated_at", 0)) <= FRESH_HOURS * 3600:
            return data
    except (FileNotFoundError, ValueError, TypeError, OSError):
        pass
    return {}


def discovery_queries():
    trend = load()
    scores = {x["category"]: x["score"] for x in trend.get("categories", [])}
    hot = set(trend.get("top_categories", [])[:MAX_EXTRA_CATEGORIES])
    hot |= CORE_CATEGORIES
    categories = list(DISCOVERY_CATALOG)
    categories.sort(key=lambda c: (c not in hot, -scores.get(c, 0)))
    ordered = []
    for category in categories:
        queries = DISCOVERY_CATALOG[category]
        if not queries: continue
        ordered.append((category, queries[0]))
        if category in hot:
            # Audio debe cubrir tanto altavoces como auriculares en el ciclo
            # frecuente, sin abrir todo el catálogo ni disparar el presupuesto.
            if category == "audio":
                candidates = list(queries[1:]) + list(CATALOG.get(category, ()))
                alternates = []
                for query in candidates:
                    if query not in {q for cat, q in ordered if cat == category} and query not in alternates:
                        alternates.append(query)
                    if len(alternates) >= 2:
                        break
            else:
                alternates = [q for q in CATALOG.get(category, ()) if q != queries[0]][:1]
            ordered.extend((category, query) for query in alternates)
    return ordered


if __name__ == "__main__":
    update()
