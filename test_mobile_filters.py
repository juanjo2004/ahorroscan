from sources.amazon import _is_smartphone_title
from sources.aliexpress import _catalog_category, _rule_for
from mobile_scanner import PHONE_QUERIES
from selection import evaluate_eligibility


def test_mobile_queries_are_validated_for_aliexpress():
    assert all(_rule_for("smartphones", query) == "smartphone_discovery" for query in PHONE_QUERIES)


def test_mobile_scanner_expands_aliexpress_queries_once(monkeypatch):
    import mobile_scanner

    aliexpress_queries = []
    monkeypatch.setattr(mobile_scanner, "init_db", lambda: None)
    monkeypatch.setattr(mobile_scanner, "buscar_amazon", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        mobile_scanner,
        "buscar_aliexpress",
        lambda query, *args, **kwargs: aliexpress_queries.append(query) or [],
    )
    monkeypatch.setattr(mobile_scanner, "select_mobile_publicable", lambda rows: [])

    mobile_scanner.scan()

    assert aliexpress_queries == ["telefonos moviles"]


def test_mobile_scanner_stops_amazon_queries_after_transient_block(monkeypatch):
    import mobile_scanner

    amazon_queries = []
    aliexpress_queries = []
    monkeypatch.setattr(mobile_scanner, "init_db", lambda: None)
    monkeypatch.setattr(
        mobile_scanner,
        "buscar_amazon",
        lambda query, *args, **kwargs: amazon_queries.append(query) or [],
    )
    monkeypatch.setattr(
        mobile_scanner,
        "amazon_last_status",
        lambda: {"failed": True, "reason": "http_5xx"},
    )
    monkeypatch.setattr(
        mobile_scanner,
        "buscar_aliexpress",
        lambda query, *args, **kwargs: aliexpress_queries.append(query) or [],
    )
    monkeypatch.setattr(mobile_scanner, "select_mobile_publicable", lambda rows: [])

    mobile_scanner.scan()

    assert amazon_queries == [mobile_scanner.PHONE_QUERIES[0]]
    assert aliexpress_queries == ["telefonos moviles"]


def test_amazon_accepts_real_smartphones():
    assert _is_smartphone_title("REDMI 17 5G, 4+128GB, Naranja")
    assert _is_smartphone_title("Samsung Galaxy S26 Ultra 5G 256GB")
    assert _is_smartphone_title("iPhone 18 Pro 256GB")
    assert _is_smartphone_title("Motorola Moto G54 4G 8GB 256GB")
    assert _is_smartphone_title("HONOR X7c 4G 8+256GB")
    assert _is_smartphone_title("Blackview BV4800 4G Rugged Smartphone")


def test_amazon_rejects_smartphone_accessories():
    blocked = (
        "Cargador inalámbrico para teléfono móvil 15W",
        "Soporte para teléfono móvil de coche",
        "Funda para iPhone 17 Pro Max",
        "Protector de pantalla para Galaxy S26",
    )
    assert all(not _is_smartphone_title(title) for title in blocked)


def test_aliexpress_catalog_keeps_real_smartphones():
    assert _catalog_category("Samsung Galaxy S26 Ultra 5G 256GB") == "smartphones"
    assert _catalog_category("iPhone 18 Pro 512GB OLED 5G") == "smartphones"
    assert _catalog_category("Motorola Moto G54 4G 8GB 256GB") == "smartphones"
    assert _catalog_category("HONOR X7c 4G 8+256GB") == "smartphones"
    assert _catalog_category("Blackview BV4800 4G Rugged Smartphone") == "smartphones"


def test_aliexpress_catalog_rejects_smartphone_accessories():
    blocked = (
        "Soporte para teléfono móvil de coche",
        "Cargador inalámbrico para teléfono móvil",
        "Funda para iPhone 17 Pro Max",
        "Protector de pantalla para Samsung Galaxy S26",
    )
    assert all(_catalog_category(title) != "smartphones" for title in blocked)


def test_mobile_selector_emits_same_title_once(monkeypatch, tmp_path):
    import mobile_channel
    from models import Offer

    monkeypatch.setattr(mobile_channel, "DB_PATH", tmp_path / "mobile.db")
    assert not hasattr(mobile_channel, "is_recent_duplicate")
    monkeypatch.setattr(mobile_channel, "mobile_recently_published", lambda **kwargs: False)
    first = Offer("amazon", "A-1", "Xiaomi Redmi Note 15 Smartphone", 200, 250,
                  "https://example.test/1", "https://example.test/1", rating=4.6,
                  reviews=1000, product_id=None)
    second = Offer("aliexpress", "B-2", "Xiaomi Redmi Note 15 Smartphone", 195, 250,
                   "https://example.test/2", "https://example.test/2", rating=4.5,
                   reviews=900, product_id=None)
    rows = [(70, first, {}, {}, "BUENA OFERTA"), (68, second, {}, {}, "BUENA OFERTA")]

    assert len(mobile_channel.select_mobile_publicable(rows)) == 1


def test_selection_blocks_accessory_misclassified_as_smartphone():
    from models import Offer
    offer = Offer(source="amazon", external_id="x", title="Cargador inalámbrico para teléfono móvil", current_price=20, reference_price=30, url="https://example.com", affiliate_url="https://example.com", image_url=None, rating=4.8, reviews=5000, category="smartphones")
    decision = evaluate_eligibility(offer, 90, "CHOLLO")
    assert not decision.eligible
    assert "smartphone_no_es_terminal" in decision.reasons

 
def test_mobile_channel_blocks_camera_lens_kits_misclassified_as_phones():
    import mobile_channel
    from models import Offer
    offer = Offer("aliexpress", "lens-kit", "Kit de filtro de lente de cámara de teléfono para iPhone",
                  12, 20, "https://example.test/product",
                  "https://example.test/affiliate", rating=4.8, reviews=1000,
                  product_id=None)
    assert mobile_channel.mobile_kind(offer) is None

 
def test_mobile_fallback_relaxes_only_quality_thresholds():
    import mobile_channel
    from models import Offer

    offer = Offer("amazon", "fallback-1", "Xiaomi Redmi Note 15 Smartphone 5G",
                  160, 200, "https://example.test/product",
                  "https://example.test/affiliate", rating=4.6, reviews=52,
                  product_id=None)
    row = (36, offer, {}, {}, "DESCARTAR")
    assert not mobile_channel.mobile_eligible(row, relaxed=False)
    assert mobile_channel.mobile_eligible(row, relaxed=True)

 
def test_mobile_channel_blocks_false_discount_above_historical_average():
    import mobile_channel
    from models import Offer
    offer = Offer("amazon", "fake-phone-discount", "Xiaomi Redmi Note 15 Smartphone 5G",
                  69.39, 141.61, "https://example.test/product",
                  "https://example.test/affiliate", rating=4.8, reviews=100,
                  product_id=None)
    row = (60, offer, {"count": 14, "average": 60.69, "minimum": 55.21}, {},
           "BUENA OFERTA")
    assert not mobile_channel.mobile_eligible(row, relaxed=False)
    assert not mobile_channel.mobile_eligible(row, relaxed=True)
