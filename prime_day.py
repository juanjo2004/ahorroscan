from __future__ import annotations

import os

PRIME_DAY_MODE = os.getenv("PRIME_DAY_MODE", "0").lower() in {"1", "true", "yes", "on"}
PRIME_DAY_MIN_RATING = float(os.getenv("PRIME_DAY_MIN_RATING", "4.31"))
PRIME_DAY_MIN_DISCOUNT = float(os.getenv("PRIME_DAY_MIN_DISCOUNT", "8"))
PRIME_DAY_MIN_REVIEWS = int(os.getenv("PRIME_DAY_MIN_REVIEWS", "0"))


def empty_history() -> dict:
    return {
        "count": 0,
        "average": None,
        "minimum": None,
        "confidence": 0.0,
    }


def history_for(regular_history: dict) -> dict:
    return empty_history() if PRIME_DAY_MODE else regular_history


PRIME_DAY_ALLOW_NON_AMAZON_FALLBACK = os.getenv("PRIME_DAY_ALLOW_NON_AMAZON_FALLBACK", "0").lower() in {"1", "true", "yes", "on"}
PRIME_DAY_FALLBACK_MIN_DISCOUNT = float(os.getenv("PRIME_DAY_FALLBACK_MIN_DISCOUNT", "15"))


def offer_allowed(offer) -> bool:
    source = (getattr(offer, "source", "") or "").lower()
    if source == "amazon":
        return True
    if not PRIME_DAY_ALLOW_NON_AMAZON_FALLBACK:
        return False
    discount = getattr(offer, "discount_pct", 0) or 0
    rating = getattr(offer, "rating", None)
    return discount >= PRIME_DAY_FALLBACK_MIN_DISCOUNT and rating is not None and rating >= PRIME_DAY_MIN_RATING


def prime_eligible(score, offer, classification) -> bool:
    if not PRIME_DAY_MODE:
        return False
    if not offer_allowed(offer):
        return False
    min_discount = PRIME_DAY_MIN_DISCOUNT if (getattr(offer, "source", "") or "").lower() == "amazon" else PRIME_DAY_FALLBACK_MIN_DISCOUNT
    if (getattr(offer, "discount_pct", 0) or 0) < min_discount:
        return False
    rating = getattr(offer, "rating", None)
    if rating is None or rating < PRIME_DAY_MIN_RATING:
        return False
    reviews = getattr(offer, "reviews", None)
    if PRIME_DAY_MIN_REVIEWS and (reviews is None or reviews < PRIME_DAY_MIN_REVIEWS):
        return False
    return True
