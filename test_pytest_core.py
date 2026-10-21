import sqlite3
from datetime import datetime, timedelta, timezone

import config
from catalog import iter_queries, query_count
from dedupe import canonical_url, product_key
from models import Offer
from publication_guard import (
    can_publish,
    record_publication,
    is_recent_duplicate,
)
from scoring import score_offer
from selection import evaluate_eligibility
from scanner import _classify_amazon
from telegram_sender import build_offer_keyboard


def make_offer(title="Producto", category="storage"):
    return Offer(
        source="amazon",
        external_id="A-1",
        title=title,
        current_price=70.0,
        reference_price=100.0,
        url="https://example.com/producto",
        affiliate_url="https://example.com/af",
        image_url="https://example.com/image.jpg",
        rating=4.7,
        reviews=5000,
        category=category,
    )


def test_catalog_modes_are_separated():
    # El catálogo completo incluye el bloque ampliado de móviles y familias Tech.
    from catalog import CATALOG
    assert query_count("full") == sum(len(queries) for queries in CATALOG.values())
    # Discovery es adaptativo: nunca baja del catálogo base y puede añadir
    # consultas a categorías calientes según el perfil de tendencias.
    assert query_count("discovery") >= 21
    discovery = list(iter_queries("discovery"))
    assert ("smartphones", "movil 5g") in discovery
    assert ("monitors", "monitor 4k") in discovery


def test_catalog_rejects_unknown_mode():
    try:
        list(iter_queries("unknown"))
    except ValueError:
        pass
    else:
        raise AssertionError("unknown scan mode must fail")


def test_canonical_url_removes_tracking_but_keeps_product_parameters():
    url = "https://SHOP.example/p/123/?utm_source=x&ref=abc&variant=black"
    assert canonical_url(url) == "https://shop.example/p/123?variant=black"


def test_product_key_prefers_stable_external_id():
    offer = make_offer()
    assert product_key(offer) == "amazon:A-1"


def test_accessory_like_product_is_blocked():
    offer = make_offer("NVMe SSD enclosure adapter USB-C")
    decision = evaluate_eligibility(offer, 90.0, "CHOLLO")
    assert not decision.eligible
    assert "tipo_producto_bloqueado" in decision.reasons


def _init_publication_db(path):
    con = sqlite3.connect(path)
    con.execute("""
        CREATE TABLE publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            source TEXT,
            external_id TEXT,
            title TEXT,
            category TEXT,
            price REAL,
            discount_pct REAL,
            score REAL,
            telegram_message_id INTEGER,
            published_at TEXT
        )
    """)
    con.commit()
    con.close()


def test_publication_guard_respects_run_limit(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)
    monkeypatch.setattr(publication_guard, "MAX_PUBLICATIONS_PER_RUN", 2)
    monkeypatch.setattr(publication_guard, "get_today_publication_count", lambda: 0)
    monkeypatch.setattr(publication_guard, "is_recent_duplicate", lambda **kwargs: (False, "ok"))

    allowed, reason = can_publish(2, 1, 90.0, 20.0)
    assert allowed is False
    assert reason == "limite_ejecucion_2"


def test_publication_guard_allows_new_product(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)
    record_publication(1, "amazon", "A-1", "Producto", "storage", 100.0, 20.0, 70.0, 123)
    allowed, reason = can_publish(0, 2, 90.0, 30.0)
    assert allowed is True
    assert reason == "publicacion_permitida"


def test_recent_same_title_is_blocked_even_with_price_improvement(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)

    published_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with sqlite3.connect(db) as con:
        con.execute(
            """INSERT INTO publications
               (product_id, source, external_id, title, category, price,
                discount_pct, score, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, "amazon", "A-1", "Producto X", "storage", 100.0,
             20.0, 70.0, 123, published_at),
        )
        con.commit()

    blocked, reason = is_recent_duplicate(
        product_id=1,
        current_price=70.0,
        current_discount_pct=50.0,
        current_title="Producto X",
    )
    assert blocked is True
    assert reason == "titulo_duplicado_reciente"


def test_recent_different_title_allows_strong_price_improvement(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)

    published_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with sqlite3.connect(db) as con:
        con.execute(
            """INSERT INTO publications
               (product_id, source, external_id, title, category, price,
                discount_pct, score, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, "amazon", "A-1", "Producto X", "storage", 100.0,
             20.0, 70.0, 123, published_at),
        )
        con.commit()

    blocked, reason = is_recent_duplicate(
        product_id=1,
        current_price=80.0,
        current_discount_pct=20.0,
        current_title="Producto X versión renovada",
    )
    assert blocked is False
    assert reason == "precio_mejora_20.0pct"


def test_can_publish_forwards_current_title_to_repeat_guard(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)
    monkeypatch.setattr(publication_guard, "get_today_publication_count", lambda: 0)

    captured = {}

    def fake_guard(**kwargs):
        captured.update(kwargs)
        return True, "titulo_duplicado_reciente"

    monkeypatch.setattr(publication_guard, "is_recent_duplicate", fake_guard)

    allowed, reason = publication_guard.can_publish(
        0,
        1,
        90.0,
        30.0,
        current_title="Producto X",
    )
    assert allowed is False
    assert reason == "titulo_duplicado_reciente"
    assert captured["current_title"] == "Producto X"


def test_recent_title_block_checks_more_than_100_publications(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)

    published_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with sqlite3.connect(db) as con:
        rows = []
        for i in range(101):
            title = "Otro producto %03d" % i
            if i == 100:
                title = "Producto objetivo"
            rows.append((1000+i, "amazon", f"A-{i}", title, "storage", 100.0, 20.0, 70.0, 100+i, published_at))
        con.executemany(
            """INSERT INTO publications
               (product_id, source, external_id, title, category, price,
                discount_pct, score, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)
        con.commit()

    blocked, reason = publication_guard.is_recent_duplicate(
        product_id=9999,
        current_price=100.0,
        current_discount_pct=20.0,
        current_title="Producto objetivo",
    )
    assert blocked is True
    assert reason == "titulo_duplicado_reciente"


def test_same_product_different_title_without_improvement_is_blocked(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)

    published_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with sqlite3.connect(db) as con:
        con.execute(
            """INSERT INTO publications
               (product_id, source, external_id, title, category, price,
                discount_pct, score, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, "amazon", "A-1", "Producto X", "storage", 100.0,
             20.0, 70.0, 123, published_at),
        )
        con.commit()

    blocked, reason = publication_guard.is_recent_duplicate(
        product_id=1, current_price=99.0, current_discount_pct=20.0,
        current_title="Producto X versión nueva",
    )
    assert blocked is True
    assert reason.startswith("publicado_hace_")


def test_exactly_seven_days_allows_same_title(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)

    published_at = (datetime.now(timezone.utc) - timedelta(days=7, seconds=1)).isoformat()
    with sqlite3.connect(db) as con:
        con.execute(
            """INSERT INTO publications
               (product_id, source, external_id, title, category, price,
                discount_pct, score, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, "amazon", "A-1", "Producto X", "storage", 100.0,
             20.0, 70.0, 123, published_at),
        )
        con.commit()

    blocked, _ = publication_guard.is_recent_duplicate(
        product_id=1, current_price=100.0, current_discount_pct=20.0,
        current_title="Producto X",
    )
    assert blocked is False


def test_title_normalization_blocks_case_accents_and_punctuation(monkeypatch, tmp_path):
    import publication_guard

    db = tmp_path / "guard.db"
    _init_publication_db(db)
    monkeypatch.setattr(publication_guard, "DB_PATH", db)

    published_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with sqlite3.connect(db) as con:
        con.execute(
            """INSERT INTO publications
               (product_id, source, external_id, title, category, price,
                discount_pct, score, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, "amazon", "A-1", "Café 4K-Pro!", "monitors", 100.0,
             20.0, 70.0, 123, published_at),
        )
        con.commit()

    blocked, reason = publication_guard.is_recent_duplicate(
        product_id=2, current_price=100.0, current_discount_pct=20.0,
        current_title="CAFE 4K PRO",
    )
    assert blocked is True
    assert reason == "titulo_duplicado_reciente"


def test_vertical_selection_forwards_title_to_repeat_guard(monkeypatch, tmp_path):
    import vertical_channel

    db = tmp_path / "vertical.db"
    monkeypatch.setattr(vertical_channel, "DB_PATH", db)

    captured = []

    def fake_guard(**kwargs):
        captured.append(kwargs)
        return True, "titulo_duplicado_reciente"

    monkeypatch.setattr(vertical_channel, "is_recent_duplicate", fake_guard)
    vertical_channel.init_channel("moda")

    class Offer:
        product_id = 123
        title = "Vestido elegante de prueba"
        category = "women_fashion"
        current_price = 49.0
        discount_pct = 20.0
        rating = 4.6
        reviews = 100

    row = (70.0, Offer(), None, None, "PUBLICAR")
    selected = vertical_channel.select_vertical_publicable([row], "moda")

    assert selected == []
    assert captured
    assert captured[0]["current_title"] == "Vestido elegante de prueba"


def test_telegram_publisher_forwards_offer_title_to_guard(monkeypatch):
    import telegram_publisher
    import telegram_sender

    captured = {}
    monkeypatch.setattr(telegram_publisher, "publishing_enabled", lambda channel: True)
    monkeypatch.setattr(telegram_publisher, "can_publish", lambda **kwargs: (captured.update(kwargs) or (True, "ok")))
    monkeypatch.setattr(telegram_sender, "format_offer", lambda *args, **kwargs: "TEST")

    import config
    monkeypatch.setattr(config, "TELEGRAM_DRY_RUN", True)

    class Offer:
        product_id = 321
        title = "Producto de integración"
        current_price = 80.0
        discount_pct = 20.0
        source = "amazon"
        external_id = "TEST-321"
        image_url = None

    row = (75.0, Offer(), None, None, "PUBLICAR")
    result = telegram_publisher.publish([row])

    assert result and result[0]["status"] == "dry_run"
    assert captured["current_title"] == "Producto de integración"


def test_source_health_unknown_without_attempts():
    assert _classify_amazon(0, 0) == "unknown"


def test_source_health_unavailable_when_all_attempts_fail():
    assert _classify_amazon(4, 4) == "unavailable"


def test_source_health_degraded_after_many_failures():
    assert _classify_amazon(6, 3) == "degraded"


def test_source_health_ok_with_small_failure_rate():
    assert _classify_amazon(10, 1) == "ok"

def test_offer_keyboard_uses_tracking_redirector(monkeypatch):
    import telegram_sender

    monkeypatch.setattr(
        telegram_sender,
        "get_or_create_product_link",
        lambda product_id, destination_url, project, channel=None: (
            f"https://tracking.example/{project}/{channel or 'unknown'}/{product_id}"
        ),
    )

    offer = make_offer()
    offer.source = "aliexpress"
    offer.product_id = 42

    keyboard = build_offer_keyboard(offer)

    assert keyboard["inline_keyboard"][0][0]["url"] == (
        "https://tracking.example/tech/telegram_tech/42"
    )


def test_amazon_offer_keyboard_uses_direct_special_link():
    offer = make_offer()
    offer.source = "amazon"
    offer.product_id = 42
    offer.affiliate_url = "https://www.amazon.es/dp/B000TEST?tag=godo00-21"

    keyboard = build_offer_keyboard(offer)

    assert keyboard["inline_keyboard"][0][0]["url"] == offer.affiliate_url


def test_tracking_link_manager_creates_and_reuses_v3(monkeypatch, tmp_path):
    import redirector.link_manager as lm

    db = tmp_path / "clicks.db"
    monkeypatch.setattr(lm, "CLICK_DB", db)
    monkeypatch.setattr(lm, "PUBLIC_BASE_URL", "https://tracking.example/go")

    first = lm.get_or_create_product_link(
        42, "https://shop.example/product/42", "tech", "telegram_tech"
    )
    second = lm.get_or_create_product_link(
        42, "https://shop.example/product/42", "tech", "telegram_tech"
    )

    assert first == second
    assert first.startswith("https://tracking.example/go/")

    import sqlite3
    with sqlite3.connect(db) as con:
        row = con.execute(
            "SELECT project, product_id, destination_url, channel FROM links_v3"
        ).fetchone()
    assert row == ("tech", 42, "https://shop.example/product/42", "telegram_tech")
