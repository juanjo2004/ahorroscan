

def test_aliexpress_noisy_results_are_rejected_by_category_guards():
    from selection import _tech_category_title_is_allowed
    assert not _tech_category_title_is_allowed("tablets", "Micrófono Lavalier Inalámbrico para iPhone y iPad")
    assert not _tech_category_title_is_allowed("components", "Cable elevador PCIe para tarjeta gráfica GPU")
    assert not _tech_category_title_is_allowed("networking", "Soporte de pared para router WiFi Mesh TP-Link Deco")
    assert not _tech_category_title_is_allowed("wearables", "Correa de cuero para Huawei Watch Fit 4")
    assert not _tech_category_title_is_allowed("gaming", "Servocontrolador + Robot Gamepad para brazo robótico")
    assert not _tech_category_title_is_allowed("power", "Placa de protección de batería 18650 con inversor UPS")


def test_brand_model_discovery_query_reaches_aliexpress_api_query_list():
    from sources.aliexpress import _production_queries, _rule_for
    requested = "xiaomi pad 7"
    rule_name = _rule_for("tablets", requested)
    assert rule_name == "future_tablets"
    queries = _production_queries(rule_name, requested)
    assert queries[0] == requested
    assert len(queries) == len(set(queries))
    assert queries == (requested,)


def test_brand_model_query_reaches_api_for_existing_and_future_rules():
    from sources.aliexpress import _production_queries, _rule_for
    cases = [("tablets", "xiaomi pad 7"), ("storage", "samsung 990 pro nvme"), ("monitors", "aoc gaming monitor")]
    for category, requested in cases:
        rule_name = _rule_for(category, requested)
        assert rule_name
        assert _production_queries(rule_name, requested)[0] == requested


def test_laptop_brand_search_does_not_accept_chargers_as_laptops():
    from selection import _tech_category_title_is_allowed
    assert not _tech_category_title_is_allowed("laptops", "Cargador original 65W para Lenovo ThinkPad X280")
    assert not _tech_category_title_is_allowed("laptops", "Adaptador AC para ordenador portátil Lenovo")


def test_brand_model_scoring_rejects_generic_or_wrong_brand_results():
    from aliexpress_classifier import Rule, score_product
    mini_rule = Rule("future_desktops", ("mini pc", "pc sobremesa"), {}, ("mini pc", "pc sobremesa"), (), (), (), ())
    generic = {"product_title": "Mini PC Windows 11, 16GB RAM", "first_level_category_name": "Computer"}
    score, reasons = score_product(generic, mini_rule, "beelink mini pc")
    assert score == 0 and "marca_modelo_no_coincide" in reasons
    laptop_rule = Rule("future_laptops", ("laptop", "notebook"), {}, ("laptop", "notebook"), (), (), (), ())
    wrong_brand = {"product_title": "Laptop ASUS Vivobook 15", "first_level_category_name": "Laptop"}
    score, reasons = score_product(wrong_brand, laptop_rule, "lenovo thinkpad")
    assert score == 0 and "marca_modelo_no_coincide" in reasons


def test_specific_queries_are_not_mixed_with_generic_aliases():
    from sources.aliexpress import _production_queries, _rule_for
    for category, query in [("storage", "samsung 990 pro nvme"), ("mice", "logitech g502 mouse"), ("desktops", "beelink mini pc")]:
        rule_name = _rule_for(category, query)
        assert rule_name
        assert _production_queries(rule_name, query) == (query,)

def test_desktop_charger_is_not_accepted_as_mini_pc():
    from selection import _tech_category_title_is_allowed
    assert not _tech_category_title_is_allowed("desktops", "Cargador adaptador de CA para Beelink Mini S12 Pro")


def test_laptop_replacement_parts_and_robot_vacuum_parts_are_rejected():
    from selection import _tech_category_title_is_allowed
    assert not _tech_category_title_is_allowed("laptops", "Cubierta de bisel LCD para Lenovo ThinkPad T420")
    assert not _tech_category_title_is_allowed("smart_home", "Filtro HEPA para Roborock S8 robot aspirador")
    assert not _tech_category_title_is_allowed("smart_home", "Caja de polvo para Roborock Qrevo Curv")


def test_future_category_scoring_can_reach_relaxed_publication_threshold():
    from aliexpress_classifier import RULE_BY_NAME, score_product
    tablet = {"product_title": "HONOR Pad X8a Tablet PC de 11 pulgadas", "first_level_category_name": "Tablet"}
    score, reasons = score_product(tablet, RULE_BY_NAME["future_tablets"], "tablet android 11 pulgadas")
    assert score >= 55 and "familia_validada_core+20" in reasons
    vacuum = {"product_title": "Robot Aspirador ABIR X9 navegación láser", "first_level_category_name": "Robot Vacuum"}
    score, reasons = score_product(vacuum, RULE_BY_NAME["future_smart_home"], "robot aspirador")
    assert score >= 55 and "familia_validada_core+20" in reasons
