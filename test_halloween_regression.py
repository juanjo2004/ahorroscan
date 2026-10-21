from datetime import date
import seasonal_queries
import seasonal_engine
import selection

def test_halloween_queries_active_on_october_18():
    rows = seasonal_queries.queries(date(2026, 10, 18))
    assert any(cat == "seasonal_halloween" for cat, _ in rows)

def test_tech_halloween_electronics_allowed_costumes_blocked():
    assert selection._tech_category_title_is_allowed("seasonal_halloween", "Proyector LED Halloween para exterior")
    assert not selection._tech_category_title_is_allowed("seasonal_halloween", "Disfraz Halloween para adulto")

def test_halloween_season_active():
    assert "halloween" in seasonal_engine.active_seasons(date(2026, 10, 18))
