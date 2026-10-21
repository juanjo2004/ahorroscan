"""Catálogo de búsquedas tecnológicas.

El catálogo completo se reserva para la recogida histórica diaria.
El descubrimiento frecuente usa un subconjunto de consultas prioritarias.
"""

CATALOG = {
    "smartphones": [
        "movil 5g", "movil 4g", "smartphone 5g", "smartphone 4g",
        "telefono movil", "telefono android", "smartphone barato", "movil barato",
        "gama media smartphone", "gama alta smartphone",
        "iphone", "google pixel", "samsung galaxy", "xiaomi redmi poco", "motorola smartphone",
        "honor smartphone", "oppo realme", "oneplus nothing phone",
        "vivo smartphone", "sony xperia", "tcl smartphone", "zte nubia",
        "asus zenfone rog phone", "nokia hmd smartphone", "doogee ulefone blackview",
    ],
    "tablets": ["tablet android", "ipad", "xiaomi pad 7", "lenovo tab p12", "samsung galaxy tab s10", "redmi pad pro"],
    "laptops": ["portatil", "macbook"],
    "desktops": ["pc sobremesa", "mini pc"],
    "monitors": ["monitor 27 144hz", "monitor 4k"],
    "televisores": ["smart tv 4k", "tv oled"],
    "networking": ["router wifi 6", "wifi mesh"],
    "storage": ["ssd nvme", "disco duro externo ssd"],
    "components": ["tarjeta grafica", "memoria ram ddr5"],
    "cpu": ["ryzen 7", "intel core i7"],
    "motherboards": ["placa base am5", "placa base lga 1851"],
    "peripherals": ["teclado mecanico", "webcam 1080p"],
    "mice": ["raton gaming", "raton inalambrico"],
    "audio": ["altavoz bluetooth", "altavoces bluetooth", "altavoz portatil", "barra de sonido", "cascos gaming", "auriculares bluetooth"],
    "smart_home": ["camara wifi", "enchufe inteligente"],
    "wearables": ["smartwatch", "smartband"],
    "gaming": ["consola gaming", "mando pc"],
    "charging": ["cargador usb c", "cargador gan"],
    "power": ["power bank", "ups"],
    "cameras": ["camara deportiva", "camara instantanea"],
    "drones": ["dron con camara", "mini dron"],
    "projectors": ["proyector 4k", "proyector portatil"],
    "vr": ["gafas vr", "accesorios vr"],
    "printers": ["impresora laser wifi", "impresora multifuncion wifi"],
    "ereaders": ["ereader", "lector ebook"],
    "microphones": ["microfono usb", "microfono streaming"],
    "accessories": ["hub usb c", "dock usb c"],
    "cables": ["cable usb c", "cable hdmi 2.1"],
}

# Catálogo de descubrimiento amplio para el canal. Una consulta por categoría
# mantiene el coste controlado; el escaneo histórico diario sigue usando CATALOG.
DISCOVERY_CATALOG = {
    "smartphones": [
        "movil 5g", "movil 4g", "smartphone 5g", "smartphone 4g",
        "telefono movil", "telefono android", "smartphone barato", "movil barato",
        "gama media smartphone", "gama alta smartphone",
        "iphone", "google pixel", "samsung galaxy", "xiaomi redmi poco", "motorola smartphone",
        "honor smartphone", "oppo realme", "oneplus nothing phone",
        "vivo smartphone", "sony xperia", "tcl smartphone", "zte nubia",
        "asus zenfone rog phone", "nokia hmd smartphone", "doogee ulefone blackview",
    ],
    "tablets": ["tablet android", "ipad"],
    "laptops": ["portatil", "lenovo thinkpad", "asus vivobook", "acer nitro laptop", "xiaomi redmibook", "huawei matebook"],
    "desktops": ["mini pc", "beelink mini pc", "minisforum mini pc", "gmktec mini pc", "geekom mini pc"],
    "monitors": ["monitor 4k", "aoc gaming monitor", "xiaomi monitor 27", "lg ultragear monitor", "gigabyte gaming monitor"],
    "televisores": ["smart tv 4k", "xiaomi tv 4k", "tcl qled tv", "hisense tv 4k", "lg oled tv"],
    "networking": ["router wifi 6", "tp-link deco mesh", "xiaomi router wifi 7", "asus router wifi 6", "gl inet travel router"],
    "storage": ["ssd nvme", "samsung 990 pro nvme", "wd black sn850x", "crucial p3 plus", "kingston nv3 ssd"],
    "components": ["tarjeta grafica", "asus geforce rtx", "gigabyte geforce rtx", "msi radeon rx", "corsair ddr5 ram"],
    "cpu": ["ryzen 7", "amd ryzen 7 9700x", "amd ryzen 5 9600x", "intel core i5 14600k", "intel core ultra 7"],
    "motherboards": ["placa base am5", "msi b850 motherboard", "asus b850 motherboard", "gigabyte b850 motherboard"],
    "peripherals": ["teclado mecanico", "logitech mx keys", "keychron mechanical keyboard", "razer blackwidow keyboard"],
    "mice": ["raton gaming", "logitech g502 mouse", "razer deathadder mouse", "steelseries gaming mouse"],
    "audio": ["altavoz bluetooth", "auriculares bluetooth", "altavoces bluetooth", "altavoz portatil", "barra de sonido", "cascos gaming", "microfono streaming"],
    "smart_home": ["enchufe inteligente", "xiaomi robot vacuum", "roborock robot aspirador", "dreame robot vacuum", "tapo camara wifi"],
    "wearables": ["smartwatch", "xiaomi smart band 9", "amazfit smartwatch", "huawei watch gt", "samsung galaxy watch"],
    "gaming": ["consola gaming", "auriculares gaming", "microfono gaming", "anbernic handheld console", "retroid pocket gaming", "8bitdo controller"],
    "charging": ["cargador gan"],
    "power": ["power bank", "anker power bank", "ugreen power bank", "baseus power bank"],
    "cameras": ["camara deportiva"],
    "projectors": ["proyector portatil", "xgimi projector", "anker nebula projector", "optoma projector", "wanbo projector"],
}


def iter_queries(mode="full"):
    if mode not in {"full", "discovery"}:
        raise ValueError(f"Modo de escaneo no válido: {mode}")
    if mode == "discovery":
        # El catálogo de descubrimiento se adapta a señales recientes de venta
        # y añade consultas propias de la temporada comercial española.
        try:
            from seasonal_queries import queries as seasonal_queries
            for category, qs in seasonal_queries():
                for query in qs:
                    yield category, query
        except Exception as exc:
            print(f"[CATALOG] Consultas estacionales no disponibles: {exc}")

        # El catálogo de descubrimiento se adapta a señales recientes de venta.
        # Si el perfil no existe o está caducado, devuelve exactamente el catálogo base.
        try:
            from trend_engine import discovery_queries
            dynamic = discovery_queries()
            if dynamic:
                # Las tendencias priorizan consultas, pero no sustituyen el
                # catálogo base: hacerlo silenciaba búsquedas de marcas/modelos.
                seen = set()
                base = ((cat, q) for cat, queries in DISCOVERY_CATALOG.items() for q in queries)
                for item in [*dynamic, *base]:
                    if item not in seen:
                        seen.add(item)
                        yield item
                return
        except Exception as exc:
            print(f"[CATALOG] Tendencias no disponibles, usando catálogo base: {exc}")

    catalog = CATALOG if mode == "full" else DISCOVERY_CATALOG
    for category, queries in catalog.items():
        for query in queries:
            yield category, query


def query_count(mode="full") -> int:
    if mode == "discovery":
        return sum(1 for _ in iter_queries("discovery"))
    catalog = CATALOG
    return sum(len(qs) for qs in catalog.values())
