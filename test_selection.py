from datetime import date
from types import SimpleNamespace
import selection
from selection import evaluate_eligibility, select_publicable
from seasonal_engine import is_seasonally_premature


def offer(category, discount, rating, reviews):
    reference = 100.0
    current = reference * (1 - discount / 100.0)
    return SimpleNamespace(
        category=category,
        title={
            'mice': 'Wireless mouse',
            'laptops': 'Laptop computer',
            'cables': 'USB-C cable',
            'charging': 'USB-C charger',
            'monitors': '4K monitor',
            'audio': 'Wireless headphones',
            'wearables': 'Smartwatch',
            'storage': 'NVMe SSD',
        }.get(category, category),
        discount_pct=discount,
        rating=rating,
        reviews=reviews,
        current_price=current,
        reference_price=reference,
    )


a = offer('mice', 50, 4.6, 12000)
b = offer('mice', 48, 4.7, 9000)
c = offer('laptops', 70, 5.0, 14)
d = offer('cables', 35, 4.8, 15000)

d1 = evaluate_eligibility(a, 60, 'BUENA OFERTA')
d2 = evaluate_eligibility(c, 60, 'INTERESANTE')
assert d1.eligible
assert d2.eligible

rows = [
    (68, a, {}, {}, 'BUENA OFERTA'),
    (67, b, {}, {}, 'BUENA OFERTA'),
    (57, d, {}, {}, 'INTERESANTE'),
]
selected = select_publicable(rows, max_publicable=1)
assert len(selected) == 1
assert selected[0][1] is a

# La selección normal sigue priorizando las categorías publicables.
assert all(row[4] != 'INTERESANTE' for row in selected)
print('OK: selección editorial, elegibilidad y diversidad por categoría')


def test_high_confidence_interesting_can_enter():
    strong = offer('charging', 34, 4.8, 1300)
    rows = [(55.7, strong, {}, {}, 'INTERESANTE')]
    selected = select_publicable(rows)
    assert len(selected) == 1
    assert selected[0][1] is strong


def test_two_products_same_category_are_allowed():
    one = offer('monitors', 40, 4.7, 5000)
    two = offer('monitors', 35, 4.6, 3000)
    one.product_id = 1001
    two.product_id = 1002
    rows = [
        (66, one, {}, {}, 'BUENA OFERTA'),
        (64, two, {}, {}, 'BUENA OFERTA'),
    ]
    selected = select_publicable(rows, max_publicable=5, max_per_category=2)
    assert len(selected) == 2


def test_smartphone_high_confidence_can_enter_with_moderate_discount():
    mobile = offer('smartphones', 12.5, 4.4, 775)
    mobile.title = 'XIAOMI REDMI Note 15 Smartphone 8+256GB 5G'
    rows = [(53.2, mobile, {}, {}, 'BUENA OFERTA')]
    selected = select_publicable(rows)
    assert len(selected) == 1
    assert selected[0][1] is mobile


def test_audio_and_wearables_are_capped_to_one_each(monkeypatch):
    monkeypatch.setattr(selection, "get_today_category_count", lambda category: 0)
    audio1 = offer('audio', 40, 4.7, 5000)
    audio2 = offer('audio', 35, 4.6, 3000)
    wear1 = offer('wearables', 40, 4.7, 5000)
    wear2 = offer('wearables', 35, 4.6, 3000)
    rows = [
        (70, audio1, {}, {}, 'BUENA OFERTA'),
        (69, audio2, {}, {}, 'BUENA OFERTA'),
        (68, wear1, {}, {}, 'BUENA OFERTA'),
        (67, wear2, {}, {}, 'BUENA OFERTA'),
    ]
    selected = select_publicable(rows, max_publicable=6, max_per_category=2)
    assert sum(r[1].category == 'audio' for r in selected) == 1
    assert sum(r[1].category == 'wearables' for r in selected) == 1


def test_accessory_like_product_is_not_publicable():
    accessory = offer('storage', 60, 4.8, 5000)
    accessory.title = 'NVMe SSD enclosure adapter USB-C'
    decision = evaluate_eligibility(accessory, 90, 'CHOLLO')
    assert not decision.eligible
    assert 'tipo_producto_bloqueado' in decision.reasons


def test_non_tech_lunchbox_is_blocked_even_if_classified_as_laptop():
    lunchbox = offer('laptops', 53, 5.0, 63)
    lunchbox.title = 'Lonchera portátil de silicona con asa, contenedor de alimentos'
    decision = evaluate_eligibility(lunchbox, 90, 'CHOLLO')
    assert not decision.eligible
    assert 'producto_fuera_de_tech' in decision.reasons


def test_brand_known_title_ranks_ahead_of_unbranded_offer(monkeypatch):
    monkeypatch.setattr(selection, "get_recent_category_counts", lambda hours: {})
    known = offer('audio', 30, 4.8, 5000)
    known.title = "JBL Auriculares Bluetooth"
    known.product_id = 1
    unknown = offer('mice', 45, 4.8, 5000)
    unknown.title = "Wireless mouse"
    unknown.product_id = 2
    rows = [(65, unknown, {}, {}, "BUENA OFERTA"), (60, known, {}, {}, "BUENA OFERTA")]

    ordered = selection._sort_for_diversity(rows, {})

    assert ordered[0][1] is known


def test_catalog_categories_all_have_title_guards():
    from catalog import CATALOG

    assert set(CATALOG).issubset(selection.TECH_CATEGORY_TITLE_TERMS)


def test_unknown_tech_category_and_wrong_product_type_are_blocked():
    assert not selection._tech_category_title_is_allowed("seasonal_halloween", "Disfraz Halloween para adulto")
    assert selection._tech_category_title_is_allowed("seasonal_halloween", "Proyector LED Halloween para exterior")
    assert not selection._tech_category_title_is_allowed("gaming", "Organizador de cuero para coche")
    assert selection._tech_category_title_is_allowed("cables", "Cable USB-C trenzado")
    assert selection._tech_category_title_is_allowed("power", "Anker 737 Portable Charger")


def test_future_christmas_product_is_blocked_in_september():
    title = 'Proyector de luz navideño, Christmas Projector Light'
    assert is_seasonally_premature(title, date(2026, 9, 22))
    assert not is_seasonally_premature(title, date(2026, 11, 15))

 
def test_relaxed_selection_allows_validated_catalog_offer_without_query_relevance(monkeypatch):
    import selection
    from models import Offer
    monkeypatch.setattr(selection, "get_recent_category_counts", lambda hours: {})
    monkeypatch.setattr(selection, "get_today_category_count", lambda category: 0)
    candidate = Offer("aliexpress", "catalog-mouse", "Ratón inalámbrico KEBIDUMEI para juegos",
                      20, 30, "https://example.test/product",
                      "https://example.test/affiliate", rating=4.5, reviews=20,
                      category="mice", product_id=None)
    row = (36, candidate, {}, {}, "DESCARTAR")
    assert not selection._row_is_publicable(row, relaxed=False)
    assert selection._row_is_publicable(row, relaxed=True)
    assert len(selection.select_publicable([row])) == 1

 
def test_relaxed_fallback_only_when_strict_pass_is_empty(monkeypatch):
    monkeypatch.setattr(selection, "get_recent_category_counts", lambda hours: {})
    monkeypatch.setattr(selection, "get_today_category_count", lambda category: 0)
    candidate = offer("mice", 20, 4.5, 20)
    rows = [(44, candidate, {}, {}, "DESCARTAR")]
    assert not selection._row_is_publicable(rows[0], relaxed=False)
    assert selection._row_is_publicable(rows[0], relaxed=True)
    selected = select_publicable(rows)
    assert len(selected) == 1 and selected[0][1] is candidate


def test_false_advertised_discount_above_historical_average_is_blocked():
    from models import Offer
    candidate = Offer("aliexpress", "fake-discount", "CUKTECH 10 GaN Super Charger",
                      69.39, 141.61, "https://example.test/product",
                      "https://example.test/affiliate", rating=4.8, reviews=23,
                      category="charging", product_id=None)
    row = (58.3, candidate, {"count": 14, "average": 60.69, "minimum": 55.21},
           {}, "INTERESANTE")
    assert not selection._row_is_publicable(row, relaxed=False)
    assert not selection._row_is_publicable(row, relaxed=True)
