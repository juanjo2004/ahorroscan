from types import SimpleNamespace
from telegram_sender import format_offer, clean_title


o = SimpleNamespace(
    title="Logitech G G502 Hero Ratón Gaming con Cable | Captor HERO 25K, RGB, Peso Personalizable, 11 Botones Programables, Memoria Integrada",
    current_price=19.99,
    reference_price=39.99,
    discount_pct=50.0,
    rating=4.6,
    reviews=1234,
    category="mice",
    affiliate_url="https://example.com/?a=1&b=2",
)

msg = format_offer(o, 78.5, "OFERTÓN")
assert "OFERTÓN" in msg
assert "19.99 €" in msg
assert "1,234" in msg
assert "Score:" not in msg
assert "Trust" not in msg
assert "🖱️ Ratones" in msg
assert "&amp;" in msg
assert len(clean_title(o.title)) <= 82
print("OK: formato Telegram limpio, seguro y sin scores internos")
