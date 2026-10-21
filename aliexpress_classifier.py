#!/usr/bin/env python3
"""
Motor de relevancia AliExpress V6.3.

Mantiene las reglas V6.1/V6.2 existentes y añade tres familias
validadas experimentalmente:

- auriculares Bluetooth
- cargadores GaN
- micrófonos USB

Este módulo NO toca SQLite, histórico, scoring ni Telegram.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    queries: tuple[str, ...]
    query_boost: dict[str, int]
    core: tuple[str, ...]
    required: tuple[tuple[str, ...], ...]
    positive: tuple[str, ...]
    hard_negative: tuple[str, ...]
    soft_negative: tuple[str, ...]


RULES = (
    # ================================================================
    # RATON GAMING
    # ================================================================
    Rule(
        "raton_gaming",
        ("raton gaming inalambrico",),
        {"raton gaming inalambrico": 12},
        (
            "raton",
            "ratón",
            "mouse",
        ),
        (
            ("gaming", "gamer", "juegos"),
        ),
        (
            "inalambrico",
            "inalámbrico",
            "wireless",
            "bluetooth",
            "2.4g",
            "sensor",
            "dpi",
            "optico",
            "óptico",
            "rgb",
            "ergonomico",
            "ergonómico",
            "paw3395",
            "polling",
            "26000dpi",
            "8k",
        ),
        (
            "patines",
            "skates",
            "feet",
            "pies de repuesto",
            "grip",
            "agarre",
            "cinta de agarre",
            "cable de carga",
            "cable de datos",
            "microinterruptor",
            "encoder",
            "codificador",
            "repuesto",
            "replacement",
            "estuche",
            "funda",
            "case",
            "adaptador",
            "adaptadores",
            "pegatina",
            "pegatinas",
            "pieza",
            "piezas",
            "dongle",
            "receptor usb",
        ),
        (),
    ),

    # ================================================================
    # SSD NVME
    # ================================================================
    Rule(
        "ssd_nvme",
        (
            "m2 nvme ssd 1tb",
            "pcie 4.0 nvme ssd",
            "ssd nvme 1tb m2",
        ),
        {
            "m2 nvme ssd 1tb": 15,
            "pcie 4.0 nvme ssd": 15,
            "ssd nvme 1tb m2": 12,
        },
        (
            "ssd",
            "nvme",
            "unidad de estado sólido",
            "unidad de estado solido",
        ),
        (),
        (
            "m.2",
            "m 2",
            "pcie",
            "pci-e",
            "gen3",
            "gen4",
            "gen5",
            "2280",
            "1tb",
            "2tb",
            "4tb",
            "500gb",
            "512gb",
            "256gb",
            "mb/s",
            "7400",
            "7000",
            "10000",
            "14000",
            "interno",
            "interna",
        ),
        (
            "disipador",
            "disipador de calor",
            "heatsink",
            "cooler",
            "radiador",
            "mini pc",
            "carcasa",
            "enclosure",
            "case",
            "adaptador",
            "adapter",
            "conmutador",
            "switch",
            "soporte",
            "base",
            "dock",
            "estuche",
            "cable",
            "cables",
            "externo",
            "external",
            "almacenamiento externo",
        ),
        ("usb",),
    ),

    # ================================================================
    # MONITOR 4K
    # ================================================================
    Rule(
        "monitor_4k",
        (
            "monitor 4k 27 pulgadas",
            "uhd monitor 27",
        ),
        {
            "monitor 4k 27 pulgadas": 15,
            "uhd monitor 27": 15,
        },
        (
            "monitor",
            "pantalla",
            "display",
        ),
        (
            ("4k", "uhd"),
        ),
        (
            "27",
            "24",
            "25",
            "32",
            "34",
            "144hz",
            "165hz",
            "180hz",
            "240hz",
            "120hz",
            "60hz",
            "hdmi",
            "displayport",
            "ips",
            "va",
            "oled",
            "freesync",
            "g-sync",
            "g sync",
            "hdr",
            "vesa",
            "3840x2160",
        ),
        (
            "cámara",
            "camara",
            "dashcam",
            "coche",
            "lente",
            "lens",
            "gafas",
            "smart glasses",
            "proyector",
            "extensor hdmi",
            "adaptador hdmi",
            "capturadora",
            "transmisor",
            "transmisión",
            "cable",
            "fuente de alimentación",
            "panel de repuesto",
            "pantalla de repuesto",
            "controladora",
            "placa controladora",
            "replacement panel",
            "replacement screen",
            "repuesto lcd",
            "pantalla de reemplazo",
            "panel de reemplazo",
            "lcd replacement",
            "repair screen",
        ),
        (
            "accesorio",
            "accesorios",
        ),
    ),

    # ================================================================
    # TECLADO MECANICO
    # ================================================================
    Rule(
        "teclado_mecanico",
        ("75 percent mechanical keyboard",),
        {"75 percent mechanical keyboard": 18},
        (
            "teclado",
            "keyboard",
        ),
        (
            ("mecanico", "mecánico", "mechanical"),
        ),
        (
            "hot-swap",
            "hotswap",
            "qmk",
            "via",
            "rgb",
            "bluetooth",
            "wireless",
            "2.4g",
            "pbt",
            "87 teclas",
            "104 teclas",
            "108 teclas",
            "75%",
            "65%",
            "60%",
            "tkl",
            "layout",
            "ansi",
            "iso",
        ),
        (
            "alfombrilla",
            "mouse pad",
            "pegatina",
            "sticker",
            "estuche",
            "funda",
            "soporte",
            "stand",
            "mesa",
            "organizador",
            "llavero",
            "juguete",
            "keycap",
            "keycaps",
            "juego de teclas",
            "juego de keycaps",
            "teclas pbt",
            "teclas de teclado",
            "switches sueltos",
            "interruptores sueltos",
            "cable de teclado",
            "placa de posicionamiento",
            "repuesto",
            "cosplay",
            "figura",
            "extractor",
            "interruptores",
            "switches",
        ),
        (),
    ),

    # ================================================================
    # AURICULARES BLUETOOTH
    # ================================================================
    Rule(
        "auriculares_bluetooth",
        (
            "auriculares bluetooth",
            "bluetooth earbuds",
            "wireless earbuds",
        ),
        {
            "auriculares bluetooth": 15,
            "bluetooth earbuds": 15,
            "wireless earbuds": 12,
        },
        (
            "auricular",
            "auriculares",
            "audifono",
            "audífono",
            "audifonos",
            "audífonos",
            "earbud",
            "earbuds",
            "earphone",
            "earphones",
            "headphone",
            "headphones",
        ),
        (
            ("bluetooth", "wireless", "tws"),
        ),
        (
            "anc",
            "cancelacion de ruido",
            "cancelación de ruido",
            "estereo",
            "estéreo",
            "hifi",
            "hi-fi",
            "llamadas",
            "deportivo",
            "deporte",
            "gaming",
        ),
        (
            "funda",
            "case",
            "estuche",
            "protector",
            "proteccion",
            "protección",
            "almohadilla",
            "almohadillas",
            "earpad",
            "earpads",
            "cable",
            "cables",
            "repuesto",
            "replacement",
            "adaptador",
            "soporte",
            "soportes",
            "gancho",
            "ganchos",
            "diadema de repuesto",
        ),
        (
            "accesorio",
            "accesorios",
        ),
    ),

    # ================================================================
    # SMARTPHONES: descubrimiento amplio 4G/5G y multimarca
    # ================================================================
    Rule(
        "smartphone_discovery",
        (
            "xiaomi smartphone", "xiaomi redmi note", "redmi note 14", "redmi note 13",
            "poco x6", "poco x7", "poco f6", "poco f7",
            "samsung galaxy a55", "samsung galaxy a56", "samsung galaxy s24", "samsung galaxy s25",
            "iphone 15", "iphone 16", "iphone 17", "google pixel 8", "google pixel 9", "google pixel 10",
            "motorola edge", "motorola moto g", "honor magic", "honor x9",
            "oppo reno", "realme gt", "oneplus nord", "nothing phone",
            "vivo v series", "sony xperia", "tcl smartphone", "zte nubia",
            "asus zenfone", "nokia smartphone", "doogee smartphone", "ulefone smartphone", "blackview smartphone",
            "smartphone 5g", "telefono movil libre", "telefonos moviles",
        ),
        {
            "movil 5g": 18, "movil 4g": 18, "telefonos moviles": 20, "telefonos moviles 5g": 20, "xiaomi movil": 18, "redmi smartphone": 18, "poco smartphone": 18, "smartphone 5g": 18, "smartphone 4g": 18,
            "telefono movil": 16, "telefono android": 16, "smartphone barato": 14, "movil barato": 14,
            "gama media smartphone": 14, "gama alta smartphone": 12,
            "iphone": 12, "google pixel": 15, "samsung galaxy": 16, "xiaomi redmi poco": 16, "motorola smartphone": 16,
            "honor smartphone": 16, "oppo realme": 15, "oneplus nothing phone": 15,
            "vivo smartphone": 15, "sony xperia": 15, "tcl smartphone": 15, "zte nubia": 15,
            "asus zenfone rog phone": 15, "nokia hmd smartphone": 14, "doogee ulefone blackview": 14,
        },
        (
            "smartphone", "iphone", "galaxy", "redmi", "xiaomi", "poco", "pixel", "oneplus",
            "oppo", "realme", "motorola", "honor", "nothing", "vivo", "xperia", "tcl",
            "zte", "nubia", "asus", "zenfone", "rog phone", "nokia", "hmd", "doogee",
            "ulefone", "blackview", "telefono movil", "telefono inteligente", "android",
        ),
        ("8gb", "12gb", "256gb", "512gb", "1tb", "amoled", "oled", "120hz", "108mp", "200mp", "nfc", "android", "ios"),
        (
            "radio de coche", "radio para coche", "radio para auto", "radio multimedia para automóvil",
            "radio multimedia para automovil", "carplay", "android auto", "unidad principal", "head unit",
            "estereo para coche", "estéreo para coche", "reproductor multimedia para automóvil",
        ),
        (
            "funda", "case", "carcasa", "protector", "cristal", "tempered", "vidrio",
            "cable", "adaptador", "adapter", "soporte", "holder", "correa", "strap",
            "estuche", "bolsa", "repuesto", "replacement", "pantalla de reemplazo", "screen protector",
            "bateria de reemplazo", "replacement battery", "pegatina", "sticker", "accesorio", "accesorios",
            "microfono", "micrófono", "lavalier", "lapiz optico", "lápiz óptico", "stylus",
            "smartwatch", "smart watch", "reloj inteligente", "smart band", "smartband",
            "fitness tracker", "pulsera inteligente", "reloj deportivo",
        ),
        ("accesorio", "accesorios"),
    ),

    # ================================================================
    # MONITOR GAMING / PRODUCTIVIDAD
    # ================================================================
    Rule(
        "monitor_gaming",
        ("monitor 27 144hz", "monitor 27 180hz", "monitor 24 144hz"),
        {"monitor 27 144hz": 18, "monitor 27 180hz": 18, "monitor 24 144hz": 15},
        ("monitor", "pantalla", "display"),
        (("144hz", "165hz", "180hz", "240hz", "120hz", "100hz", "144 hz", "165 hz"),),
        ("27", "24", "25", "32", "34", "ips", "va", "oled", "hdmi", "displayport", "freesync", "g-sync", "hdr", "qhd", "2k", "fhd"),
        (
            "cámara", "camara", "dashcam", "coche", "lente", "lens", "gafas", "proyector",
            "extensor hdmi", "adaptador hdmi", "capturadora", "transmisor", "cable", "fuente de alimentación",
            "panel de repuesto", "pantalla de repuesto", "replacement panel", "replacement screen",
            "repuesto lcd", "pantalla de reemplazo", "panel de reemplazo", "lcd replacement", "repair screen",
            "controladora", "placa controladora", "accesorio", "accesorios", "carcasa",
        ),
        ("accesorio", "accesorios"),
    ),

    # ================================================================
    # CARGADOR GAN
    # ================================================================
    Rule(
        "cargador_gan",
        (
            "cargador gan",
            "gan charger",
            "gan pd charger",
        ),
        {
            "cargador gan": 15,
            "gan charger": 15,
            "gan pd charger": 12,
        },
        (
            "cargador",
            "charger",
            "adaptador de corriente",
            "power adapter",
        ),
        (
            ("gan",),
        ),
        (
            "usb-c",
            "usb c",
            "type-c",
            "type c",
            "pd",
            "power delivery",
            "carga rapida",
            "carga rápida",
            "fast charge",
            "65w",
            "67w",
            "100w",
            "120w",
            "140w",
            "160w",
            "200w",
            "240w",
        ),
        (
            "cable",
            "cables",
            "soporte",
            "soportes",
            "funda",
            "estuche",
            "repuesto",
            "replacement",
            "enchufe de coche",
            "adaptador usb",
            "adaptador de audio",
            "hub",
            "dock",
            "estacion de carga",
            "estación de carga",
            "cargador inalambrico",
            "cargador inalámbrico",
        ),
        (
            "accesorio",
            "accesorios",
        ),
    ),

    # ================================================================
    # MICROFONO USB
    # ================================================================
    Rule(
        "microfono_usb",
        (
            "gaming microphone usb",
            "microfono condensador usb",
            "streaming microphone usb",
        ),
        {
            "gaming microphone usb": 18,
            "microfono condensador usb": 15,
            "streaming microphone usb": 15,
        },
        (
            "microfono",
            "micrófono",
            "microphone",
        ),
        (
            (
                "usb",
                "usb-c",
                "type-c",
                "type c",
            ),
        ),
        (
            "condensador",
            "condenser",
            "streaming",
            "podcast",
            "vlog",
            "grabacion",
            "grabación",
            "voz",
            "pc",
            "ordenador",
            "computadora",
            "gaming",
            "gamer",
            "rgb",
            "ganancia",
            "gain",
            "mute",
            "silencio",
            "cancelacion de ruido",
            "cancelación de ruido",
        ),
        (
            "auriculares bluetooth",
            "auriculares inalambricos",
            "auriculares inalámbricos",
            "auriculares tws",
            "bluetooth earbuds",
            "wireless earbuds",
            "earbud",
            "earbuds",
            "headphone",
            "headphones",
            "lavalier",
            "solapa",
            "cable",
            "cables",
            "soporte",
            "soportes",
            "funda",
            "fundas",
            "estuche",
            "estuches",
            "repuesto",
            "replacement",
            "adaptador",
            "mezclador",
            "mezcla",
            "mixer",
            "interfaz de audio",
            "audio interface",
            "consola de mezcla",
        ),
        (
            "brazo",
            "brazos",
            "shock mount",
            "pop filter",
            "filtro pop",
            "espuma",
            "windshield",
            "accesorio",
            "accesorios",
        ),
    ),
)


# Familias futuras: reglas de recolección histórica.
# Son deliberadamente independientes del publicador: permiten construir
# histórico antes de activar los canales y después se endurecerán con datos reales.
FUTURE_CATEGORY_TERMS = {
    # Halloween seasonal families are intentionally enabled for discovery.
    # Product-quality, duplicate, price-history and publication guards remain active.
    "seasonal_halloween": ("halloween", "disfraz", "disfraces", "calabaza", "pumpkin", "terror", "bruja", "maquillaje halloween", "fiesta halloween"),
    "seasonal_halloween_home": ("halloween", "decoracion", "decoración", "luces", "calabaza", "luz", "proyector halloween"),
    "seasonal_halloween_party": ("halloween", "fiesta", "maquillaje", "accesorios halloween", "decoracion fiesta halloween"),
    # Familias Tech que el descubrimiento dinámico emitía pero V6.3 omitía.
    "tablets": ("tablet", "ipad", "galaxy tab", "xiaomi pad", "lenovo tab"),
    "laptops": ("laptop", "notebook", "macbook", "portatil gaming", "ordenador portatil"),
    "desktops": ("mini pc", "pc sobremesa", "desktop", "gaming pc", "barebone pc"),
    "televisores": ("smart tv", "tv 4k", "televisor", "oled tv", "qled tv"),
    "networking": ("router wifi", "wifi mesh", "router wifi 6", "wifi 7 router"),
    "components": ("tarjeta grafica", "gpu", "memoria ram ddr5", "placa base", "motherboard"),
    "cpu": ("ryzen", "intel core", "procesador amd", "cpu intel"),
    "motherboards": ("placa base am5", "placa base lga", "motherboard am5"),
    "smart_home": ("enchufe inteligente", "robot aspirador", "camara wifi", "sensor inteligente"),
    "wearables": ("smartwatch", "smartband", "reloj inteligente", "fitness tracker"),
    "gaming": ("consola gaming", "mando pc", "gamepad", "gaming handheld", "steam deck"),
    "power": ("power bank", "ups", "sai", "bateria externa"),
    "cameras": ("camara deportiva", "camara instantanea", "action camera", "webcam 4k"),
    "projectors": ("proyector 4k", "proyector portatil", "mini projector", "proyector laser"),
    "drones": ("dron con camara", "mini dron", "drone 4k"),
    "vr": ("gafas vr", "vr headset", "virtual reality"),
    "printers": ("impresora laser wifi", "impresora multifuncion", "impresora 3d"),
    "ereaders": ("ereader", "e-reader", "lector ebook", "kindle"),
    "keyboards": ("teclado mecanico", "keyboard 75", "teclado gaming"),
    "peripherals": ("teclado mecanico", "webcam 1080p", "capturadora video"),
    "women_fashion": ("vestido", "chaqueta mujer", "ropa mujer", "falda", "blusa"),
    "men_fashion": ("camisa hombre", "chaqueta hombre", "ropa hombre", "pantalon", "vaqueros"),
    "footwear": ("zapatillas", "zapatos", "calzado", "sandalias"),
    "bags": ("bolso", "mochila", "bolsa viaje"),
    "accessories": ("gafas de sol", "reloj mujer", "cinturon", "bufanda"),
    "sportswear": ("ropa deportiva", "zapatillas running", "mallas deportivas"),
    "underwear": ("ropa interior mujer", "ropa interior hombre", "sujetador"),
    "skincare": ("serum facial", "crema facial", "protector solar"),
    "haircare": ("secador pelo", "plancha pelo", "cepillo pelo"),
    "makeup": ("maquillaje rostro", "paleta maquillaje", "base maquillaje"),
    "grooming": ("afeitadora electrica", "recortadora barba", "maquina afeitar"),
    "personal_care": ("cepillo dental electrico", "masajeador corporal", "depiladora"),
    "baby": ("silla bebe coche", "monitor bebe", "bebe"),
    "toys": ("lego", "juguetes educativos", "juguete"),
    "kids": ("ropa niños", "mochila infantil", "niños"),
    "school": ("material escolar", "calculadora escolar", "mochila escolar"),
    "maternity": ("embarazo", "lactancia", "maternidad"),
    "fitness": ("mancuernas", "banco pesas", "fitness"),
    "running": ("zapatillas running", "reloj running", "running"),
    "cycling": ("bicicleta carretera", "accesorios ciclismo", "ciclismo"),
    "outdoor": ("mochila trekking", "chaqueta montaña", "trekking"),
    "camping": ("tienda campaña", "saco dormir", "camping"),
    "team_sports": ("balon futbol", "equipacion futbol", "futbol"),
    "dog": ("comida perro", "cama perro", "perro"),
    "cat": ("comida gato", "rascador gato", "gato"),
    "pet_care": ("cepillo mascota", "fuente agua mascota", "cuidado mascota"),
    "pet_accessories": ("correa perro", "transportin mascota", "accesorios mascota"),
    "aquarium": ("acuario", "filtro acuario", "pecera"),
    "car_accessories": ("accesorios coche", "organizador coche", "coche"),
    "car_electronics": ("cargador coche usb", "radio coche", "electronica coche"),
    "motorcycle": ("casco moto", "guantes moto", "moto"),
    "dashcams": ("dashcam", "camara coche", "camara salpicadero"),
    "ev": ("cargador coche electrico", "accesorios coche electrico", "vehiculo electrico"),
    "mobility": ("patinete electrico", "accesorios patinete", "movilidad"),
    "power_tools": ("taladro bateria", "sierra circular", "herramienta electrica"),
    "hand_tools": ("juego herramientas", "llave carraca", "herramientas manuales"),
    "workshop": ("banco trabajo", "caja herramientas", "taller"),
    "hardware": ("tornillos", "ferreteria", "herrajes"),
    "garden_tools": ("herramientas jardin", "cortasetos", "jardin"),
    "irrigation": ("riego automatico", "programador riego", "riego"),
    "luggage": ("maleta cabina", "maleta viaje", "equipaje"),
    "travel_accessories": ("almohada viaje", "adaptador viaje", "accesorios viaje"),
    "hotels": ("hotel españa", "hotel vacaciones", "hotel"),
    "flights": ("vuelos baratos españa", "vuelos europa", "vuelos"),
    "car_rental": ("alquiler coche", "rent a car españa", "alquiler coche"),
}

FUTURE_RULES = tuple(
    Rule(
        f"future_{category}",
        tuple(terms[:2]),
        {q: 10 for q in terms[:2]},
        terms,
        (),
        terms,
        ("funda", "repuesto", "replacement", "sticker", "pegatina"),
        (),
    )
    for category, terms in FUTURE_CATEGORY_TERMS.items()
)

RULE_BY_NAME = {r.name: r for r in (*RULES, *FUTURE_RULES)}


def norm(s: str) -> str:
    t = (s or "").lower()

    table = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
        }
    )

    return " ".join(
        t.translate(table).split()
    )


def contains(
    text: str,
    terms: tuple[str, ...] | list[str],
) -> list[str]:
    return [
        term
        for term in terms
        if norm(term) in text
    ]


def _looks_like_replacement_monitor(title: str) -> bool:
    """Detecta paneles/pantallas de sustitución sin bloquear monitores completos."""
    t = norm(title)

    visual = any(
        x in t
        for x in (
            "pantalla",
            "panel",
            "lcd",
        )
    )

    replacement_ctx = any(
        x in t
        for x in (
            "para monitor",
            "compatible con monitor",
            "monitor lg",
            "monitor dell",
            "monitor samsung",
            "replacement",
            "repuesto",
            "reemplazo",
            "repair",
            "para lg",
            "para dell",
            "para samsung",
            "lcd original",
        )
    )

    model_ref = (
        re.search(
            r"\b[a-z]{1,8}\d{2,}[a-z0-9-]*\b",
            t,
        )
        is not None
    )

    return (
        visual
        and replacement_ctx
        and model_ref
    )


def score_product(
    product: dict,
    rule: Rule,
    query: str,
) -> tuple[int, list[str]]:
    title = norm(
        str(
            product.get(
                "product_title",
                "",
            )
        )
    )

    category = norm(
        f"{product.get('first_level_category_name', '')} "
        f"{product.get('second_level_category_name', '')}"
    )

    reasons: list[str] = []

    # Guardas estrictas para que radios multimedia y sistemas CarPlay de coche
    # no se confundan con teléfonos Android por compartir la palabra Android.
    if rule.name == "smartphone_discovery":
        vehicle_head_unit_terms = (
            "radio de coche", "radio para coche", "radio para auto",
            "radio multimedia", "unidad principal", "head unit",
            "carplay", "android auto", "para toyota", "para hyundai",
            "para volkswagen", "para nissan", "para jeep", "para bmw",
            "para audi", "para chevrolet", "para ford", "para kia",
            "para mazda", "para honda",
        )
        if any(term in title for term in vehicle_head_unit_terms):
            return 0, ["producto_automovil_no_smartphone"]

        # No basta con mencionar Android o 5G: exigir al menos una señal de
        # teléfono físico o una marca/modelo reconocible.
        phone_identity_terms = (
            "smartphone", "iphone", "galaxy", "redmi", "xiaomi", "poco",
            "pixel", "oneplus", "oppo", "realme", "motorola", "honor",
            "nothing phone", "vivo", "xperia", "zenfone", "rog phone",
            "blackview", "doogee", "ulefone", "nokia", "hmd", "nubia",
            "zte", "tcl", "telefono movil", "teléfono móvil",
            "telefono inteligente", "teléfono inteligente",
        )
        if not any(term in title for term in phone_identity_terms):
            return 0, ["sin_identidad_de_smartphone"]

    if not contains(
        title,
        rule.core,
    ):
        return 0, ["sin_core"]

    # Las APIs de afiliación pueden ignorar parte de la consulta de marca y
    # devolver productos genéricos. Exigir coincidencia explícita para evitar
    # contabilizar resultados irrelevantes como éxito de una búsqueda de marca.
    brand_query_terms = {
        "xiaomi pad 7": ("xiaomi",), "lenovo tab p12": ("lenovo",),
        "samsung galaxy tab s10": ("samsung", "galaxy tab"), "redmi pad pro": ("redmi",),
        "lenovo thinkpad": ("lenovo", "thinkpad"), "asus vivobook": ("asus", "vivobook"),
        "acer nitro laptop": ("acer", "nitro"), "xiaomi redmibook": ("xiaomi", "redmibook"),
        "huawei matebook": ("huawei", "matebook"), "beelink mini pc": ("beelink",),
        "minisforum mini pc": ("minisforum",), "gmktec mini pc": ("gmktec",), "geekom mini pc": ("geekom",),
        "aoc gaming monitor": ("aoc",), "xiaomi monitor 27": ("xiaomi",),
        "lg ultragear monitor": ("lg", "ultragear"), "gigabyte gaming monitor": ("gigabyte",),
        "xiaomi tv 4k": ("xiaomi",), "tcl qled tv": ("tcl",), "hisense tv 4k": ("hisense",),
        "lg oled tv": ("lg", "oled"), "tp-link deco mesh": ("tp-link", "deco"),
        "xiaomi router wifi 7": ("xiaomi",), "asus router wifi 6": ("asus",),
        "gl inet travel router": ("gl inet", "gl-inet"), "samsung 990 pro nvme": ("samsung", "990 pro"),
        "wd black sn850x": ("wd", "sn850x"), "crucial p3 plus": ("crucial", "p3 plus"),
        "kingston nv3 ssd": ("kingston", "nv3"), "asus geforce rtx": ("asus",),
        "gigabyte geforce rtx": ("gigabyte",), "msi radeon rx": ("msi",), "corsair ddr5 ram": ("corsair",),
        "amd ryzen 7 9700x": ("amd", "9700x"), "amd ryzen 5 9600x": ("amd", "9600x"),
        "intel core i5 14600k": ("intel", "14600k"), "intel core ultra 7": ("intel", "ultra 7"),
        "msi b850 motherboard": ("msi", "b850"), "asus b850 motherboard": ("asus", "b850"),
        "gigabyte b850 motherboard": ("gigabyte", "b850"), "logitech mx keys": ("logitech", "mx keys"),
        "keychron mechanical keyboard": ("keychron",), "razer blackwidow keyboard": ("razer", "blackwidow"),
        "logitech g502 mouse": ("logitech", "g502"), "razer deathadder mouse": ("razer", "deathadder"),
        "steelseries gaming mouse": ("steelseries",), "xiaomi robot vacuum": ("xiaomi",),
        "roborock robot aspirador": ("roborock",), "dreame robot vacuum": ("dreame",),
        "tapo camara wifi": ("tapo",), "xiaomi smart band 9": ("xiaomi",),
        "amazfit smartwatch": ("amazfit",), "huawei watch gt": ("huawei",),
        "samsung galaxy watch": ("samsung", "galaxy watch"), "anbernic handheld console": ("anbernic",),
        "retroid pocket gaming": ("retroid",), "8bitdo controller": ("8bitdo",),
        "anker power bank": ("anker",), "ugreen power bank": ("ugreen",), "baseus power bank": ("baseus",),
        "xgimi projector": ("xgimi",), "anker nebula projector": ("anker", "nebula"),
        "optoma projector": ("optoma",), "wanbo projector": ("wanbo",),
    }
    expected_brand = brand_query_terms.get(query)
    if expected_brand and not all(term in title for term in expected_brand):
        return 0, ["marca_modelo_no_coincide"]

    # En consultas de marca de smartphones, la API puede devolver productos
    # similares de otras marcas. No permitimos que un Pixel aparezca como
    # resultado de una consulta Motorola/Honor/etc.
    if rule.name == "smartphone_discovery":
        expected_brand_terms = {
            "iphone": ("iphone",),
            "google pixel": ("google pixel", "pixel"),
            "samsung galaxy": ("samsung", "galaxy"),
            "xiaomi redmi poco": ("xiaomi", "redmi", "poco"),
            "motorola smartphone": ("motorola",),
            "honor smartphone": ("honor",),
            "oppo realme": ("oppo", "realme"),
            "oneplus nothing phone": ("oneplus", "nothing"),
            "vivo smartphone": ("vivo",),
            "sony xperia": ("sony", "xperia"),
            "tcl smartphone": ("tcl",),
            "zte nubia": ("zte", "nubia"),
            "asus zenfone rog phone": ("asus", "zenfone", "rog phone"),
            "nokia hmd smartphone": ("nokia", "hmd"),
            "doogee ulefone blackview": ("doogee", "ulefone", "blackview"),
        }
        expected = expected_brand_terms.get(query)
        if expected and not any(term in title for term in expected):
            return 0, ["marca_no_coincide"]

    score = 35
    reasons.append(
        "producto_principal"
    )

    query_boost = rule.query_boost.get(
        query,
        0,
    )

    score += query_boost

    if query_boost:
        reasons.append(
            f"consulta_especifica+{query_boost}"
        )

    for group in rule.required:
        hits = contains(
            title,
            group,
        )

        if hits:
            score += 15

            reasons.append(
                "requisito:" + ",".join(hits)
            )
        else:
            score -= 15

            reasons.append(
                "falta:" + "/".join(group)
            )

    positive = contains(
        title,
        rule.positive,
    )

    score += min(
        30,
        5 * len(positive),
    )

    if positive:
        reasons.append(
            "positivos:"
            + ",".join(positive[:8])
        )

    negative = contains(
        title,
        rule.hard_negative,
    )

    if negative:
        score -= min(
            95,
            75 + 8 * (len(negative) - 1),
        )

        reasons.append(
            "bloqueos:"
            + ",".join(negative[:8])
        )

    soft = contains(
        title,
        rule.soft_negative,
    )

    if soft:
        score -= min(
            10,
            5 * len(soft),
        )

        reasons.append(
            "avisos:"
            + ",".join(soft[:5])
        )

    if any(
        x in category
        for x in (
            "perifericos",
            "componentes de ordenadores",
            "monitores",
            "audio",
            "electronica",
        )
    ):
        score += 10
        reasons.append(
            "categoria_util"
        )

    if rule.name == "raton_gaming":
        if negative:
            score = min(
                score,
                5,
            )

    elif rule.name == "ssd_nvme":
        if any(
            x in title
            for x in (
                "mini pc",
                "carcasa",
                "enclosure",
                "adaptador",
                "conmutador",
                "disipador",
                "soporte",
                "dock",
                "externo",
                "external",
                "usb",
            )
        ):
            score = min(
                score,
                10,
            )

        if not any(
            x in title
            for x in (
                "tb",
                "gb",
            )
        ):
            score = min(
                score,
                55,
            )

    elif rule.name == "monitor_4k":
        if not any(
            x in title
            for x in (
                "monitor",
                "pantalla",
                "display",
            )
        ):
            return 0, reasons + [
                "sin_tipo_monitor"
            ]

        if not any(
            x in title
            for x in (
                "4k",
                "uhd",
            )
        ):
            score = min(
                score,
                50,
            )

        if _looks_like_replacement_monitor(title):
            score = min(
                score,
                5,
            )

            reasons.append(
                "bloqueo:panel_pantalla_repuesto_contexto_modelo"
            )

    elif rule.name == "teclado_mecanico":
        if not any(
            x in title
            for x in (
                "teclado",
                "keyboard",
            )
        ):
            return 0, reasons + [
                "sin_tipo_teclado"
            ]

        if any(
            x in title
            for x in (
                "keycap",
                "keycaps",
                "juego de teclas",
                "teclas pbt",
                "teclas de teclado",
                "switches sueltos",
                "interruptores sueltos",
            )
        ):
            score = min(
                score,
                15,
            )

    # Las familias nuevas tenían un techo de puntuación cercano a 40-50,
    # inferior al umbral de publicación incluso cuando eran productos reales.
    # Bonificación limitada a resultados con core coincidente y sin negativos
    # duros; los filtros de categoría, precio, reseñas y valoración siguen mandando.
    if rule.name.startswith("future_") and score > 0 and not negative:
        score += 20
        reasons.append("familia_validada_core+20")

    return (
        max(
            0,
            min(
                100,
                score,
            ),
        ),
        reasons,
    )


def label(score: int) -> str:
    if score >= 80:
        return "MUY RELEVANTE"

    if score >= 70:
        return "RELEVANTE"

    if score >= 55:
        return "DUDOSO"

    return "NO RELEVANTE"
