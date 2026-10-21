from monetization_engine import _normalize_project


def test_normalize_hogar_clickref():
    assert _normalize_project("hogar:leroy-merlin:SKU123") == "hogar"


def test_normalize_tech_clickref():
    assert _normalize_project("tech:amazon:B07TEST") == "tech"


def test_normalize_channel_projects():
    assert _normalize_project("instagram_hogar") == "hogar"
    assert _normalize_project("telegram_tech") == "tech"


def test_unknown_project_is_preserved():
    assert _normalize_project("gaming") == "gaming"


def test_normalize_channel_projects_are_preserved():
    from monetization_engine import _channel
    assert _channel("telegram_tech", "tech") == "telegram_tech"
    assert _channel(None, "tech") == "unknown"


def test_parse_awin_clickref_metadata():
    from monetization_engine import _parse_clickref
    ref = _parse_clickref("hogar:leroy-merlin:SKU123")
    assert ref["project"] == "hogar"
    assert ref["merchant"] == "leroy-merlin"
    assert ref["external_id"] == "SKU123"


def test_parse_channel_clickref():
    from monetization_engine import _parse_clickref
    ref = _parse_clickref("telegram_hogar:amazon:SKU123")
    assert ref["project"] == "hogar"
    assert ref["channel"] == "telegram_hogar"


def test_merchant_key_normalizes_spaces_and_hyphens():
    from monetization_engine import _merchant_key
    assert _merchant_key("Leroy Merlin") == "leroymerlin"
    assert _merchant_key("leroy-merlin") == "leroymerlin"
