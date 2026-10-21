from datetime import date

from sources.aliexpress import _catalog_category
from seasonal_engine import is_seasonally_premature


def test_aliexpress_catalog_rejects_lunchbox_from_tech():
    title = "Lonchera portátil de silicona con asa, contenedor de alimentos"
    assert _catalog_category(title) is None


def test_portable_speaker_is_not_classified_as_laptop():
    title = "Tribit Altavoz Bluetooth portátil 90W StormBox Blast"
    assert _catalog_category(title) == "audio"


def test_christmas_is_not_premature_inside_campaign():
    title = "Proyector de luz navideño, Christmas Projector Light"
    assert is_seasonally_premature(title, date(2026, 10, 31))
    assert not is_seasonally_premature(title, date(2026, 11, 1))


print("OK: guardas de canal Tech y estacionalidad")
