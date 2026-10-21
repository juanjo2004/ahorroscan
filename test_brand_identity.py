import sqlite3

from brand_identity import extract_brand
from database import upsert_product
from models import Offer


def test_extracts_known_brand_from_title_start():
    assert extract_brand("Logitech G305 LIGHTSPEED Ratón") == "Logitech"
    assert extract_brand("XIAOMI POCO M8 5G Smartphone") == "Xiaomi"
    assert extract_brand("8BitDo Retro R8 Bluetooth Mouse") == "8BitDo"
    assert extract_brand("Garmin Edge 530 Bundle") == "Garmin"
    assert extract_brand("Reolink Argus Eco Security Camera") == "Reolink"
    assert extract_brand("Wacom One Creative Pen Display") == "Wacom"


def test_does_not_infer_brand_from_compatibility_text():
    assert extract_brand("Funda compatible con Apple iPhone") is None


def test_upsert_persists_inferred_brand(monkeypatch, tmp_path):
    db_path = tmp_path / "offers.db"
    monkeypatch.setattr("database.DB_PATH", db_path)
    offer = Offer(
        source="amazon", external_id="test-1",
        title="Razer BlackWidow Mechanical Keyboard",
        current_price=79.0, reference_price=99.0,
        url="https://example.test", affiliate_url="https://example.test",
        category="peripherals",
    )

    product_id = upsert_product(offer)
    with sqlite3.connect(db_path) as con:
        brand = con.execute(
            "SELECT brand FROM products WHERE id=?", (product_id,)
        ).fetchone()[0]

    assert brand == "Razer"
    assert offer.brand == "Razer"
