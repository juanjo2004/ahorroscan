from types import SimpleNamespace
from scoring import score_offer, classify_offer
from selection import evaluate_eligibility

CASES = [
    ("A: descuento 60%, 4.8★, 20k reseñas", 60, 4.8, 20000),
    ("B: descuento 45%, 4.6★, 5k reseñas", 45, 4.6, 5000),
    ("C: descuento 70%, 5.0★, 14 reseñas", 70, 5.0, 14),
    ("D: descuento 35%, 4.8★, 15k reseñas", 35, 4.8, 15000),
    ("E: descuento 55%, 4.1★, 2.5k reseñas", 55, 4.1, 2500),
    ("F: descuento 40%, 4.5★, 100 reseñas", 40, 4.5, 100),
]
HISTORY = {"count": 0, "average": None, "minimum": None}
rows = []
for name, discount, rating, reviews in CASES:
    offer = SimpleNamespace(
        source="amazon",
        current_price=100.0,
        original_price=100.0 / (1 - discount / 100.0),
        reference_price=100.0 / (1 - discount / 100.0),
        discount_pct=discount,
        rating=rating,
        reviews=reviews,
        category="cables",
    )
    score, breakdown = score_offer(offer, HISTORY)
    label = classify_offer(score, offer)
    decision = evaluate_eligibility(offer, score, label)
    rows.append((score, name, label, breakdown["deal_score"], breakdown["trust_score"], breakdown["confidence_factor"], decision.eligible))
rows.sort(reverse=True, key=lambda x: x[0])
print("=== CALIBRACIÓN DEL SCORE ===")
for i, (score, name, label, deal, trust, factor, eligible) in enumerate(rows, 1):
    print(f"{i:02d}. {score:6.2f} | {label:<12} | Deal {deal:5.1f} | Trust {trust:5.1f} | conf {factor:.2f} | {'ELEGIBLE' if eligible else 'NO'} | {name}")

by_name = {r[1]: r for r in rows}
# Safety property: the extreme-discount, low-review item must not be publishable.
assert not by_name["C: descuento 70%, 5.0★, 14 reseñas"][6]
# Strongly reviewed item should remain eligible under the same price signal.
assert by_name["F: descuento 40%, 4.5★, 100 reseñas"][6]
# Highly trusted high-discount case should outrank the low-review outlier.
assert by_name["A: descuento 60%, 4.8★, 20k reseñas"][0] > by_name["C: descuento 70%, 5.0★, 14 reseñas"][0]
print("OK: gate y calibración separan atractivo del precio de confianza")
