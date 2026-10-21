from datetime import datetime, timedelta, timezone
import sqlite3
from models import Offer
from database import DB_PATH, init_db, upsert_product, save_price_snapshot, get_history_stats
from scoring import score_offer, classify_offer

offer = Offer(
    source="test", external_id="test-quality-v4", title="Test",
    current_price=50.0, reference_price=100.0,
    url="https://example.com/test", affiliate_url="https://example.com/test?tag=test",
    rating=4.5, reviews=1000, category="test"
)
init_db()
pid = upsert_product(offer)
now = datetime.now(timezone.utc)
yesterday = (now.date() - timedelta(days=1)).isoformat()
with sqlite3.connect(DB_PATH) as con:
    con.execute("DELETE FROM price_history WHERE product_id=?", (pid,))
    con.execute("INSERT INTO price_history(product_id, price, captured_at, capture_date) VALUES (?, ?, ?, ?)", (pid, 60.0, (now-timedelta(days=1)).isoformat(), yesterday))
    con.commit()
history = get_history_stats(pid, 30)
score, breakdown = score_offer(offer, history)
classification = classify_offer(score)
assert history["count"] == 1
assert score > 0
assert classification in {"CHOLLO", "BUENA OFERTA", "OFERTA", "DESCARTAR"}
save_price_snapshot(pid, offer.current_price)
print("OK: test_core", score, history, breakdown, classification)
