from types import SimpleNamespace
from scoring import score_offer

def calc(discount, rating, reviews):
    offer = SimpleNamespace(source="amazon", current_price=100.0, discount_pct=discount, rating=rating, reviews=reviews)
    return score_offer(offer, {"count": 0, "average": None, "minimum": None})[0]

a = calc(60, 4.8, 20000)
c = calc(70, 5.0, 14)
assert a > c
assert calc(45, 4.6, 5000) > calc(35, 4.8, 15000)
print("OK: casos de calibración controlados")
