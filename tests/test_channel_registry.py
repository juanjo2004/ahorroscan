from channel_registry import categories_for_channel, channels, families, is_active, planned_channels


def test_active_channels_are_explicit():
    assert all(is_active(name) for name in ("tech", "hogar", "moda", "mascotas", "moviles", "deportes"))
    assert not is_active("belleza")


def test_future_channel_families_exist():
    assert "moda" in families()
    assert "belleza" in families()
    assert "automovil" in families()
    assert "viajes" in families()


def test_channel_category_mapping():
    assert "smartphones" in categories_for_channel("tech")
    assert "cleaning" in categories_for_channel("hogar")
    assert "women_fashion" in categories_for_channel("moda")


def test_planned_channels_never_activate_accidentally():
    assert set(planned_channels()) >= {"belleza", "familia", "deporte", "automovil", "bricolaje", "viajes"}
