from types import SimpleNamespace
from scoring import score_offer, classify_offer

base_history = {"count": 0, "average": None, "minimum": None}
strong = SimpleNamespace(discount_pct=45.0, current_price=30.0, rating=4.6, reviews=12000, source="amazon")
weak = SimpleNamespace(discount_pct=70.0, current_price=30.0, rating=5.0, reviews=6, source="amazon")

s1,b1 = score_offer(strong, base_history)
s2,b2 = score_offer(weak, base_history)
assert s1 > s2
assert b2["confidence_factor"] < 1
assert classify_offer(s1, strong) in {"INTERESANTE", "BUENA OFERTA", "OFERTÓN", "CHOLLO"}
assert classify_offer(s2, weak) != "CHOLLO"
print("OK: Deal Score + Trust Score + confidence gate")
