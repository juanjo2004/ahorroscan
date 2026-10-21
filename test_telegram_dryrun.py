from types import SimpleNamespace
from telegram_copy import format_offer
from dedupe import product_key, similar_title

o = SimpleNamespace(
    title="Logitech G G502 Hero Ratón Gaming con Cable | Captor HERO 25K, RGB",
    current_price=27.99,
    reference_price=59.99,
    discount_pct=53.3,
    rating=4.6,
    reviews=39000,
    category="mice",
    affiliate_url="https://example.com/deal",
    label="BUENA OFERTA",
    source="amazon",
    external_id="B07TEST",
)
msg = format_offer(o)
assert "Score:" not in msg
assert "Trust" not in msg
assert "🖱️ Ratones" in msg
assert "-53%" in msg
assert product_key(o) == "amazon:B07TEST"
assert similar_title(o.title, o.title) == 1.0
print("OK: presentación Telegram y deduplicación por producto")
