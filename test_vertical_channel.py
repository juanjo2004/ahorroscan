from types import SimpleNamespace
import sqlite3

import vertical_channel


def test_title_duplicate_from_other_source_id_is_blocked(monkeypatch, tmp_path):
    monkeypatch.setattr(vertical_channel, "DB_PATH", tmp_path / "vertical.db")
    vertical_channel.init_channel("moda")
    old_offer = SimpleNamespace(
        product_id=10, source="amazon", external_id="old",
        title="Columbia Chaqueta Impermeable Hombre",
        category="men_fashion", current_price=59.0, discount_pct=30.0,
        image_url=None, affiliate_url="https://example.test",
        rating=4.6, reviews=1000,
    )
    vertical_channel.record_publication("moda", old_offer, 70.0, 100)

    assert vertical_channel.already_published(
        "moda", 99, current_title="Columbia Chaqueta Impermeable Hombre"
    )
    assert not vertical_channel.already_published(
        "deportes", 99, current_title="Columbia Chaqueta Impermeable Hombre"
    )


def test_continuity_fallback_does_not_repeat_recent_title(monkeypatch, tmp_path):
    db_path = tmp_path / "fallback.db"
    monkeypatch.setattr(vertical_channel, "DB_PATH", db_path)
    vertical_channel.init_channel("moda")
    old_offer = SimpleNamespace(
        product_id=10, source="amazon", external_id="old",
        title="Columbia Chaqueta Impermeable Hombre",
        category="men_fashion", current_price=59.0, discount_pct=30.0,
        image_url=None, affiliate_url="https://example.test",
        rating=4.6, reviews=1000,
    )
    vertical_channel.record_publication("moda", old_offer, 70.0, 100)
    with sqlite3.connect(db_path) as con:
        con.execute("UPDATE fashion_publications SET published_at=datetime('now','-1 day')")
    monkeypatch.setattr(vertical_channel, "is_recent_duplicate", lambda **kwargs: (False, "ok"))
    candidate = SimpleNamespace(
        product_id=99, source="amazon", external_id="new",
        title=old_offer.title, category="men_fashion",
        current_price=55.0, discount_pct=35.0, rating=4.8, reviews=2000,
    )

    selected = vertical_channel.select_vertical_publicable(
        [(70.0, candidate, {}, {}, "BUENA OFERTA")], "moda"
    )

    assert selected == []


def test_same_title_is_selected_once_per_run(monkeypatch, tmp_path):
    monkeypatch.setattr(vertical_channel, "DB_PATH", tmp_path / "batch.db")
    monkeypatch.setattr(vertical_channel, "is_recent_duplicate", lambda **kwargs: (False, "ok"))
    first = SimpleNamespace(
        product_id=1, title="Skechers Slip-ins Max Cushioning", category="women_fashion",
        discount_pct=30.0, current_price=70.0, rating=4.7, reviews=500,
    )
    second = SimpleNamespace(
        product_id=2, title="Skechers Slip-ins Max Cushioning", category="footwear",
        discount_pct=28.0, current_price=72.0, rating=4.6, reviews=400,
    )
    rows = [
        (70.0, first, {}, {}, "BUENA OFERTA"),
        (68.0, second, {}, {}, "BUENA OFERTA"),
    ]

    selected = vertical_channel.select_vertical_publicable(rows, "moda")

    assert len(selected) == 1


def test_moda_blocks_anime_cosplay_products():
    assert not vertical_channel.vertical_title_allowed(
        "moda", "Disfraz de Anime Eromanga Sensei, camisón y traje cosplay"
    )
    assert vertical_channel.vertical_title_allowed(
        "moda", "Chaqueta impermeable para hombre"
    )
