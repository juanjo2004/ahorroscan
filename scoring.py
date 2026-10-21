import math

from seasonal_engine import seasonal_score


HISTORY_MIN_SAMPLES = 3


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(float(v), hi))


def deal_score(offer, history):
    """Atractivo económico separado de confianza, con histórico conservador."""
    discount = offer.discount_pct or 0.0
    parts = {}

    parts["discount"] = clamp(discount / 50.0) * 60.0

    count = int(history.get("count", 0) or 0)
    avg = history.get("average")
    prior_min = history.get("minimum")
    confidence = float(history.get("confidence", 0.0) or 0.0)

    # No usamos el histórico como evidencia fuerte hasta tener 3 días previos.
    if (
        count >= HISTORY_MIN_SAMPLES
        and avg
        and avg > 0
        and offer.current_price < avg
    ):
        pct = (avg - offer.current_price) / avg * 100.0
        parts["vs_average"] = (
            clamp(pct / 30.0) * 25.0 * confidence
        )
    else:
        parts["vs_average"] = 0.0

    if (
        count >= HISTORY_MIN_SAMPLES
        and prior_min
        and prior_min > 0
        and offer.current_price < prior_min
    ):
        pct = (prior_min - offer.current_price) / prior_min * 100.0
        parts["vs_prior_minimum"] = (
            clamp(pct / 20.0) * 15.0 * confidence
        )
    else:
        parts["vs_prior_minimum"] = 0.0

    return round(sum(parts.values()), 2), parts


def trust_score(offer):
    parts = {}

    rating = offer.rating or 0.0

    if rating <= 0:
        parts["rating"] = 0.0
    else:
        parts["rating"] = clamp(
            (rating - 3.5) / 1.5
        ) * 55.0

    reviews = offer.reviews or 0

    parts["reviews"] = (
        clamp(math.log10(1 + reviews) / 5.0)
        * 35.0
    )

    parts["source_reliability"] = (
        10.0 if offer.source == "amazon" else 8.0
    )

    return round(sum(parts.values()), 2), parts


def publication_score(deal, trust):
    return round(
        deal * 0.62 + trust * 0.38,
        2,
    )


def confidence_factor(rating, reviews):
    if reviews is None:
        factor = 0.70
    elif reviews < 10:
        factor = 0.75
    elif reviews < 50:
        factor = 0.85
    elif reviews < 200:
        factor = 0.93
    else:
        factor = 1.0

    if rating is not None and rating < 4.0:
        factor *= 0.80
    elif rating is not None and rating < 4.2:
        factor *= 0.92

    return factor


def score_offer(offer, history=None):
    history = history or {
        "count": 0,
        "average": None,
        "minimum": None,
        "confidence": 0.0,
    }

    deal, deal_parts = deal_score(
        offer,
        history,
    )

    trust_raw, trust_parts = trust_score(
        offer,
    )

    factor = confidence_factor(
        offer.rating,
        offer.reviews,
    )

    trust = round(
        trust_raw * factor,
        2,
    )

    total = publication_score(
        deal,
        trust,
    )

    seasonal_boost, seasonal_matches = seasonal_score(
        getattr(offer, "title", ""),
        getattr(offer, "category", None),
    )
    total = round(total + seasonal_boost, 2)

    return total, {
        "deal_score": deal,
        "trust_score": trust,
        "trust_raw": trust_raw,
        "confidence_factor": factor,
        "publication_score": total,
        "seasonal_boost": seasonal_boost,
        "seasonal_matches": seasonal_matches,
        "history_count": history.get("count", 0),
        "history_confidence": history.get("confidence", 0.0),
        "deal_parts": deal_parts,
        "trust_parts": trust_parts,
    }


def classify_offer(score, offer=None):
    offer = offer or type("O", (), {})()

    reviews = getattr(
        offer,
        "reviews",
        None,
    ) or 0

    rating = getattr(
        offer,
        "rating",
        None,
    ) or 0

    discount = getattr(
        offer,
        "discount_pct",
        None,
    ) or 0

    if (
        score >= 82
        and reviews >= 200
        and rating >= 4.4
        and discount >= 20
    ):
        return "CHOLLO"

    if (
        score >= 72
        and reviews >= 50
        and rating >= 4.2
        and discount >= 15
    ):
        return "OFERTÓN"

    if (
        score >= 60
        and reviews >= 15
        and rating >= 4.0
        and discount >= 12
    ):
        return "BUENA OFERTA"

    if score >= 50 and discount >= 12:
        return "INTERESANTE"

    return "DESCARTAR"
