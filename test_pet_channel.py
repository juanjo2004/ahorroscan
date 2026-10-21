from types import SimpleNamespace

from pet_channel import pet_kind, select_pet_publicable


def offer(title, category):
    return SimpleNamespace(
        title=title, category=category, product_id=None,
        discount_pct=20, rating=4.5, reviews=100,
        current_price=19.9, source="amazon", external_id=title,
        image_url="https://example.com/a.jpg", affiliate_url="https://example.com",
    )


def row(title, category, score=80):
    return (score, offer(title, category), [], {}, "CHOLLO")


def test_pet_kind():
    assert pet_kind(offer("Cama para perro grande", "dog")) == "dog"
    assert pet_kind(offer("Rascador para gato", "cat")) == "cat"
    assert pet_kind(offer("Fuente de agua para mascota", "pet_care")) == "pet_care"


def test_pet_kind_accessories():
    assert pet_kind(offer("Correa perro reflectante", "pet_accessories")) == "pet_accessories"
    assert pet_kind(offer("Filtro para acuario", "aquarium")) == "aquarium"

def test_blocked_replacement():
    assert pet_kind(offer("Repuesto filtro acuario", "aquarium")) is None


def test_diversity():
    rows = [
        row("Comida perro", "dog", 90),
        row("Comida gato", "cat", 89),
        row("Cepillo mascota", "pet_care", 88),
        row("Correa perro", "pet_accessories", 87),
        row("Filtro acuario", "aquarium", 86),
        row("Cama perro", "dog", 85),
    ]
    selected = select_pet_publicable(rows, max_publicable=5)
    assert len(selected) == 5
    assert {r[1].category for r in selected} == {"dog", "cat", "pet_care", "pet_accessories", "aquarium"}


def test_same_title_is_selected_once_per_run():
    rows = [
        row("Cama ortopédica para perro", "dog", 90),
        row("Cama ortopédica para perro", "dog", 85),
    ]
    assert len(select_pet_publicable(rows, max_publicable=5)) == 1


def test_quality():
    bad = SimpleNamespace(**offer("Cama perro", "dog").__dict__)
    bad.rating = 3.4
    assert pet_kind(bad) == "dog"
    assert not select_pet_publicable([(80, bad, [], {}, "CHOLLO")], max_publicable=1)
def test_old_product_is_allowed_again_after_seven_days(tmp_path, monkeypatch):
    import sqlite3
    import pet_channel

    db = tmp_path / "pet-publications.db"
    monkeypatch.setattr(pet_channel, "DB_PATH", db)
    pet_channel.init_pet_publications()
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO pet_publications(product_id, source, external_id, title, category, published_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (999, "amazon", "TEST-999", "Producto mascota", "dog", "2020-01-01 00:00:00"),
        )
        conn.commit()

    blocked, reason = pet_channel.is_recent_pet_duplicate(999, "Producto mascota", 19.9, 20)
    assert blocked is False
    assert reason == "sin_repeticion_reciente"


def test_old_family_variant_is_allowed_again_after_seven_days(tmp_path, monkeypatch):
    import sqlite3
    import pet_channel

    db = tmp_path / "pet-publications.db"
    monkeypatch.setattr(pet_channel, "DB_PATH", db)
    pet_channel.init_pet_publications()
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO pet_publications(product_id, source, external_id, title, category, published_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (998, "amazon", "TEST-998", "morpilot Transportín Perro Gato Negro 44 x 31 x 34 cm", "pet_accessories", "2020-01-01 00:00:00"),
        )
        conn.commit()

    blocked, reason = pet_channel.is_recent_pet_duplicate(
        997,
        "morpilot Transportín Perro Gato Gris 44 x 31 x 34 cm",
        19.9,
        20,
    )
    assert blocked is False
    assert reason == "sin_repeticion_reciente"
