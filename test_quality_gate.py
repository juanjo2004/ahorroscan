from types import SimpleNamespace
from scoring import score_offer, classify_offer

weak = SimpleNamespace(
    discount_pct=70.0, current_price=30.0, rating=5.0, reviews=6
)
strong = SimpleNamespace(
    discount_pct=45.0, current_price=30.0, rating=4.6, reviews=12000
)

weak_score, weak_breakdown = score_offer(
    weak, {"count": 0, "average": None, "minimum": None}
)
strong_score, _ = score_offer(
    strong, {"count": 0, "average": None, "minimum": None}
)

assert classify_offer(weak_score, weak.discount_pct, weak.rating, weak.reviews) != "CHOLLO"
assert strong_score > weak_score
assert weak_breakdown["confidence_factor"] < 1.0
print("OK: quality gate evita premiar en exceso productos con pocas reseñas")
