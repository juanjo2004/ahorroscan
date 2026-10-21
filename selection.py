from dataclasses import dataclass
import os

from publication_guard import is_recent_duplicate, get_recent_category_counts, get_today_category_count
from seasonal_engine import is_seasonally_premature
from brand_identity import extract_brand
from product_relevance import is_repair_related


MIN_DISCOUNT_PCT = 8.0
PRIME_DAY_BROAD_MODE = os.getenv("PRIME_DAY_BROAD_MODE", "0").lower() in {"1", "true", "yes", "on"}
MIN_RATING = 4.31 if PRIME_DAY_BROAD_MODE else 3.5
MIN_REVIEWS = 0 if PRIME_DAY_BROAD_MODE else 5

# La diversidad es una preferencia, no un cuello de botella absoluto.
# Primera plaza: una oferta por categoría. Segunda plaza: se permite
# otra si sigue estando entre las mejores candidatas.
MAX_PER_CATEGORY = 2
MAX_PUBLICABLE = 12

# Preferencia editorial del canal Tech: dar visibilidad a móviles y
# evitar que audio/wearables ocupen demasiadas plazas consecutivas.
CATEGORY_SELECTION_PRIORITY = {
    "smartphones": 100,
    "tablets": 55,
    "laptops": 50,
    "monitors": 45,
    "televisores": 40,
    "gaming": 35,
    "storage": 30,
    "desktops": 25,
    "audio": -20,
    "wearables": -25,
}

CATEGORY_MAX_OVERRIDES = {
    "smartphones": 2,
    "audio": 1,
    "wearables": 1,
}

# Categorías de alta demanda: un descuento del 20%+ ya puede ser
# suficientemente atractivo aunque todavía no haya 200 valoraciones.
# Se mantienen rating y reseñas mínimas para no abrir la puerta a basura.
HIGH_INTEREST_CATEGORIES = {
    "smartphones",
    "tablets",
    "laptops",
    "monitors",
    "televisores",
    "gaming",
    "wearables",
    "audio",
    "storage",
    "desktops",
}

HIGH_INTEREST_MIN_SCORE = 52.0
HIGH_INTEREST_MIN_DISCOUNT = 20.0
HIGH_INTEREST_MIN_RATING = 4.2
HIGH_INTEREST_MIN_REVIEWS = 30

# Publicación normal: estas clasificaciones llegan al canal.
PUBLISHABLE_LABELS = {"CHOLLO", "OFERTÓN", "BUENA OFERTA", "INTERESANTE"}

# Apertura controlada del embudo:
# permitimos algunos "INTERESANTE" cuando las señales de confianza
# son claramente altas, sin tocar los límites de Telegram.
INTERESTING_MIN_SCORE = 55.0
INTERESTING_MIN_DISCOUNT = 20.0
INTERESTING_MIN_RATING = 4.4
INTERESTING_MIN_REVIEWS = 200

BLOCKED_PRODUCT_TERMS = {
    "keycap",
    "keycaps",
    "replacement",
    "repuesto",
    "recambio",
    "replacement screen",
    "pantalla de reemplazo",
    "carcasa",
    "case",
    "housing",
    "adapter",
    "adaptador",
    "dongle",
    "stand",
    "soporte",
    "cover",
    "funda",
}

# Piezas de recambio y piezas auxiliares de bajo interés editorial.
# Se excluyen del canal Tech aunque puedan pertenecer técnicamente
# a una categoría tecnológica.
LOW_INTEREST_TECH_TERMS = {
    # Accesorios de cámara/fotografía que no son cámaras completas.
    "jaula de cámara",
    "jaula para cámara",
    "jaula para camara",
    "camera cage",
    "matte box",
    "mini matte box",
    "empuñadura superior",
    "empuñadura para cámara",
    "empuñadura para camara",
    "top handle",
    "follow focus",
    "zapata fría",
    "zapata fria",
    "cold shoe",
    "rig para cámara",
    "rig para camara",
    "cage for camera",
    "filtro de estrella",
    "filtro de estrella variable",
    "filtro de lentes",
    "filtro para lentes",
    "filtros para lentes",
    # Accesorios y piezas de impresoras 3D/CNC.
    "piezas de impresora",
    "pieza de impresora",
    "piezas para impresora",
    "pieza para impresora",
    "ventilador de impresora",
    "filtro para impresora",
    "filtros de impresora",
    "ventilador para impresora",
    "ventilador 3d",
    "pieza para cnc",
    "piezas para cnc",
    # Accesorios automoción/generalistas.
    "sensor de aparcamiento",
    "sensor parking",
    "parktronic",
    "cámara de visión trasera",
    "camara de vision trasera",
    "cámara para coche",
    "camara para coche",
    "para coche",
    "para automóvil",
    "para automovil",
    "para motocicleta",
    "para moto",
    "para camión",
    "para camion",
    "para vehículo",
    "para vehiculo",
    "12v 24v para coche",
}

REPLACEMENT_PART_TERMS = {
    "pieza de repuesto",
    "piezas de repuesto",
    "pieza de recambio",
    "piezas de recambio",
    "repuesto para",
    "repuestos para",
    "recambio para",
    "recambios para",
    "replacement part",
    "replacement parts",
    "spare part",
    "spare parts",
    "repair part",
    "repair parts",
    "replacement component",
    "replacement components",
    "pieza sustitución",
    "piezas sustitución",
    "componente de sustitución",
    "componentes de sustitución",

    # Piezas auxiliares típicas de impresoras 3D / CNC / maquinaria.
    "guía lineal",
    "guia lineal",
    "riel de guía",
    "riel de guia",
    "riel lineal",
    "riel de guía lineal",
    "linear guide",
    "linear rail",
    "guide rail",
    "carro deslizante",
    "carro lineal",
    "carro de guía",
    "carro de guia",
    "bloque de guía",
    "bloque de guia",
    "cojinete lineal",
    "rodamiento lineal",
    "husillo de bolas",
    "ball screw",
    "lead screw",
    "tornillo de avance",

    # Pequeños elementos industriales que no aportan interés editorial
    # como oferta generalista.
    "zumbador activo",
    "zumbador pasivo",
    "buzzer activo",
    "buzzer pasivo",
    "piezo buzzer",
}

AUDIO_DAILY_LIMIT = 2

SMARTPHONE_ACCESSORY_TERMS = {
    "cargador para",
    "cargador inalámbrico",
    "cargador de teléfono",
    "charger for",
    "soporte para",
    "holder for",
    "mount for",
    "stand for",
    "funda para",
    "case for",
    "carcasa para",
    "cover for",
    "protector para",
    "protector de pantalla",
    "screen protector",
    "cristal templado",
    "cable para",
    "adaptador para",
    "adapter for",
    "batería de reemplazo",
    "replacement battery",
    "pantalla de reemplazo",
    "replacement screen",
    "repuesto para",
    "replacement for",
    "accesorio para",
    "accessory for",
    "jaula para",
    "cage for",
    "mango para",
    "grip for",
    "trípode para",
    "tripod for",
    "stylus para",
    "lápiz óptico para",
    "gimbal para",
    "lente para",
    "lente de",
    "objetivo para",
    "macro lens",
    "wide angle lens",
    "lens for",
    "camera lens",
    "selfie stick",
    "palo selfie",
    "flash para",
    "filtro cpl",
    "kit de lentes",
}

# Productos claramente ajenos a Tech. Se comprueban por título además de la
# categoría porque términos ambiguos como "portátil" pueden contaminar
# búsquedas de portátiles con productos cotidianos (p. ej. "lonchera portátil").
TECH_NON_TECH_TERMS = {
    "lonchera",
    "fiambrera",
    "tupper",
    "tupperware",
    "contenedor de alimentos",
    "recipiente de comida",
    "bolsa térmica",
    "bolsa termica",
    "caja de almuerzo",
    "sartén",
    "sarten",
    "cacerola",
    "vajilla",
    "cubiertos",
    "mantel",
    "ropa",
    "camiseta",
    "camisa",
    "pantalón",
    "pantalon",
    "vestido",
    "zapatos",
    "zapatillas",
    "maquillaje",
    "cosmética",
    "cosmetica",
    "perfume",
    "juguete",
    "peluche",
    "joyería",
    "joyeria",
    "collar",
    "pulsera",
    "mascota",
    "perro",
    "gato",
    "comida para",
    "utensilio de cocina",
    "muñeco",
    "muñecos",
    "bloques de construcción",
    "bloques de construccion",
    "figura coleccionable",
    "disfraz",
    "disfraces",
    "costume",
    "costumes",
    "ropa de halloween",
    "traje de halloween",
    "traje inflable",
}

TECH_BLOCKED_CATEGORIES = set()


def _tech_title_is_allowed(title):
    text = " ".join((title or "").lower().split())
    return not any(term in text for term in TECH_NON_TECH_TERMS)


def _looks_like_low_interest_tech_item(title):
    text = " ".join((title or "").lower().split())
    if any(term in text for term in LOW_INTEREST_TECH_TERMS):
        return True

    patterns = (
        # Impresora 3D/CNC + pieza/componente específico.
        ("impresora 3d", "pieza"),
        ("impresora 3d", "piezas"),
        ("impresora 3d", "ventilador"),
        ("impresora 3d", "filtro"),
        ("impresora 3d", "motor"),
        ("impresora 3d", "sensor"),
        ("impresora 3d", "placa"),
        ("impresora 3d", "correa"),
        ("impresora 3d", "rodamiento"),
        ("impresora 3d", "carbón"),
        ("impresora 3d", "carbon"),
        ("cnc", "pieza"),
        ("cnc", "piezas"),
        ("cnc", "riel"),
        ("cnc", "carro"),
        # Cámara + accesorio explícito.
        ("cámara", "jaula"),
        ("camara", "jaula"),
        ("cámara", "empuñadura"),
        ("camara", "empuñadura"),
        ("cámara", "matte box"),
        ("camara", "matte box"),
        ("cámara", "filtro"),
        ("camara", "filtro"),
        ("cámara", "zapata fría"),
        ("camara", "zapata fria"),
        # Automoción: no confundir con una cámara/webcam normal.
        ("coche", "sensor"),
        ("coche", "cámara"),
        ("coche", "camara"),
        ("coche", "cargador"),
        ("coche", "mando"),
        ("coche", "soporte"),
        ("coche", "pantalla"),
        ("coche", "luz"),
        ("automóvil", "accesorio"),
        ("automovil", "accesorio"),
    )
    return any(all(part in text for part in pattern) for pattern in patterns)

def _looks_like_replacement_part(title):
    text = " ".join((title or "").lower().split())

    if is_repair_related(text):
        return True

    if any(term in text for term in REPLACEMENT_PART_TERMS):
        return True

    # Patrones estructurales típicos de piezas de sustitución.
    replacement_patterns = (
        ("para impresora", "pieza"),
        ("para impresora 3d", "pieza"),
        ("para impresora", "repuesto"),
        ("para impresora 3d", "repuesto"),
        ("para cnc", "pieza"),
        ("para cnc", "repuesto"),
        ("para máquina", "pieza"),
        ("para maquina", "pieza"),
        ("para máquina", "repuesto"),
        ("para maquina", "repuesto"),
    )

    if any(
        all(part in text for part in pattern)
        for pattern in replacement_patterns
    ):
        return True

    return False


TECH_CATEGORY_TITLE_TERMS = {
    "seasonal_halloween": ("proyector", "projector", "luz led", "led halloween", "laser", "luz laser", "luz de halloween", "proyector halloween", "proyector de halloween"),
    "smartphones": (
        "smartphone",
        "iphone",
        "galaxy",
        "redmi",
        "xiaomi",
        "poco",
        "pixel",
        "oneplus",
        "oppo",
        "realme",
        "motorola",
        "honor",
        "nothing phone",
        "vivo",
        "xperia",
        "tcl",
        "zte",
        "nubia",
        "zenfone",
        "rog phone",
        "nokia",
        "hmd",
        "doogee",
        "ulefone",
        "blackview",
        "fairphone",
        "telefono movil",
        "teléfono móvil",
        "telefono inteligente",
        "teléfono inteligente",
    ),
    "tablets": (
        "tablet",
        "ipad",
        "galaxy tab",
    ),
    "laptops": (
        "laptop",
        "portátil",
        "portatil",
        "macbook",
        "notebook",
        "ordenador portátil",
        "ordenador portatil",
        "pc portátil",
        "pc portatil",
    ),
    "desktops": (
        "desktop",
        "pc sobremesa",
        "mini pc",
        "mini-pc",
        "all in one",
        "aio",
    ),
    "televisores": (
        "smart tv",
        "televisor",
        "televisión",
        "television",
        "oled tv",
        "qled",
        "tv 4k",
        "tv 8k",
    ),
    "monitors": (
        "monitor",
        "pantalla de ordenador",
        "monitor gaming",
    ),
    "storage": (
        "ssd",
        "nvme",
        "disco duro",
        "hard drive",
    ),
    "components": (
        "gpu",
        "tarjeta gráfica",
        "tarjeta grafica",
        "memoria ram",
        "ram ddr",
        "placa base",
        "motherboard",
    ),
    "cpu": (
        "ryzen",
        "intel core",
        "procesador",
        "cpu",
    ),
    "keyboards": (
        "teclado",
        "keyboard",
    ),
    "mice": (
        "ratón",
        "raton",
        "mouse",
    ),
    "audio": (
        "auricular",
        "headphone",
        "headset",
        "earbud",
        "altavoz",
        "speaker",
        "soundbar",
        "dac",
        "amplificador de auriculares",
    ),
    "wearables": (
        "smartwatch",
        "reloj inteligente",
        "smart band",
        "smartband",
        "fitness tracker",
    ),
    "gaming": (
        "consola",
        "gamepad",
        "mando pc",
        "steam deck",
        "gaming handheld",
        "tarjeta de memoria",
    ),
    "charging": (
        "cargador",
        "charger",
        "power bank",
        "gan",
    ),
    "networking": (
        "router",
        "wifi",
        "wi-fi",
        "mesh",
        "switch ethernet",
        "access point",
        "placa de desarrollo",
    ),
    "cameras": (
        "cámara",
        "camara",
        "camera",
        "webcam",
        "action cam",
        "dashcam",
    ),
    "drones": (
        "drone",
        "dron",
        "quadcopter",
    ),
    "projectors": (
        "proyector",
        "projector",
    ),
    "vr": (
        "vr headset",
        "gafas vr",
        "realidad virtual",
    ),
    "printers": (
        "impresora",
        "printer",
        "impresora 3d",
        "3d printer",
    ),
    "microphones": (
        "micrófono",
        "microfono",
        "microphone",
    ),
    "smart_home": (
        "smart home", "enchufe inteligente", "interruptor inteligente",
        "sensor inteligente", "zigbee", "robot aspirador",
    ),
    "motherboards": ("placa base", "motherboard", "mainboard"),
    "peripherals": ("teclado", "keyboard", "webcam"),
    "power": (
        "power bank", "batería externa", "bateria externa", "portable charger",
        "portable power station", "ups",
    ),
    "accessories": ("hub usb", "usb hub", "dock usb", "docking station"),
    "cables": ("cable usb", "cable hdmi", "hdmi cable", "cable ethernet"),
    "ereaders": ("ereader", "e-reader", "kindle", "lector ebook", "lector de libros electrónicos"),
}

TECH_CATEGORY_TITLE_BLOCKED = {
    "smartphones": (
        "microfono",
        "micrófono",
        "cargador",
        "funda",
        "case",
        "protector",
        "soporte",
        "cable",
        "lente",
        "lens",
        "objetivo",
        "macro",
        "gran angular",
        "wide angle",
        "teleobjetivo",
        "trípode",
        "tripode",
        "selfie stick",
        "palo selfie",
        "filtro cpl",
        "kit de lentes",
    ),
    "tablets": (
        "stylus", "lápiz óptico", "lapiz optico", "punta de lápiz", "punta de lapiz",
        "funda", "case", "protector", "soporte", "microfono", "micrófono",
        "microphone", "lavalier", "cargador", "cable", "adaptador", "adaptador de",
    ),
    "components": (
        "cable elevador", "riser cable", "soporte de montaje", "soporte gpu",
        "carcasa externa", "gpu dock", "cable de extensión", "cable de extension",
        "adaptador", "bracket", "soporte vertical",
    ),
    "networking": (
        "soporte de pared", "base de almacenamiento", "soporte de exhibición",
        "modulo m.2", "módulo m.2", "antena", "cable", "adaptador", "carcasa",
    ),
    "power": (
        "placa de protección", "placa de proteccion", "bms", "18650", "inversor de energía",
        "inversor de energia", "células de batería", "celdas de bateria",
    ),
    "wearables": (
        "correa", "strap", "adaptador de brazalete", "soporte de conexión", "accesorio para reloj",
    ),
    "gaming": (
        "robot", "brazo robótico", "brazo robotico", "servocontrolador", "receptor usb para brazo",
    ),
    "smart_home": (
        "accesorios para robot", "accesorios para aspiradora", "toallitas", "fregonas laterales",
        "tanque de agua", "repuesto", "replacement", "caja de polvo", "cubo de basura",
        "mopa", "filtro hepa", "cepillo lateral", "bolsa para polvo", "dust bin",
        "dust box", "water tank", "side brush", "vacuum filter", "mop pad",
    ),
    "laptops": (
        "ratón", "raton", "mouse", "altavoz", "speaker", "bombilla",
        "lonchera", "fiambrera", "luz portátil", "luz portatil",
        "soporte para portátil", "soporte para laptop", "cargador", "adaptador de ca",
        "adaptador ac", "fuente de alimentación", "fuente de alimentacion",
        "batería compatible", "bateria compatible", "teclado de repuesto",
        "pantalla de repuesto", "ventilador de repuesto", "bisagra para",
        "cubierta de bisel", "carcasa de marco", "marco frontal de pantalla",
        "lcd bezel", "screen bezel", "replacement hinge", "hinge for lenovo",
        "replacement keyboard", "replacement screen", "replacement fan",
    ),
    "desktops": (
        "cargador", "adaptador de ca", "adaptador ac", "fuente de alimentación",
        "fuente de alimentacion", "cable de alimentación", "cable de alimentacion",
        "soporte", "carcasa para", "repuesto", "replacement", "ventilador para",
    ),
    "televisores": (
        "juguete",
        "muñeco",
        "muñecos",
        "bloques de construcción",
        "figura coleccionable",
        "tarjeta de memoria",
        "para tv",
        "para televisión",
        "para television",
        "mando a distancia",
        "soporte de tv",
        "antena de tv",
    ),
    "printers": (
        "papel térmico",
        "papel termico",
        "rollo de papel",
        "hotend",
        "boquilla",
        "extrusora",
        "termistor",
        "bloque de calor",
    ),
    "projectors": (
        "gafas 3d",
        "gafas 3D",
        "obturador activo",
        "lámpara proyector",
        "lampara proyector",
        "luz navideña",
        "luz navidena",
        "luz de halloween",
    ),
    "cameras": (
        "lente para",
        "objetivo para",
        "filtro para",
        "filtros para",
        "soporte para cámara",
        "soporte para camara",
        "enfoque de seguimiento",
        "follow focus",
        "rig para cámara",
        "rig para camara",
    ),
    "drones": (
        "tarjeta de memoria",
        "memoria tf",
        "micro sd",
        "microsd",
        "hélice",
        "helice",
        "batería para",
        "bateria para",
        "cargador para",
        "mando para",
    ),
}


def _tech_category_title_is_allowed(category, title):
    cat = (category or "").lower().strip()
    text = " ".join((title or "").lower().split())

    if cat in TECH_BLOCKED_CATEGORIES or cat not in TECH_CATEGORY_TITLE_TERMS:
        return False

    if not _tech_title_is_allowed(text):
        return False

    blocked = TECH_CATEGORY_TITLE_BLOCKED.get(cat, ())
    if any(term in text for term in blocked):
        return False

    required = TECH_CATEGORY_TITLE_TERMS.get(cat)
    if required and not any(term in text for term in required):
        return False

    return True


def _smartphone_is_real_product(title):
    text = " ".join((title or "").lower().split())

    device_terms = (
        "smartphone",
        "iphone",
        "galaxy",
        "redmi",
        "xiaomi",
        "poco",
        "pixel",
        "oneplus",
        "oppo",
        "realme",
        "motorola",
        "moto ",
        "honor",
        "nothing phone",
        "vivo",
        "xperia",
        "tcl",
        "zte",
        "nubia",
        "asus",
        "zenfone",
        "rog phone",
        "nokia",
        "hmd",
        "doogee",
        "ulefone",
        "blackview",
        "fairphone",
        "telefono móvil",
        "teléfono móvil",
        "telefono movil",
        "teléfono movil",
        "móvil",
        "movil",
        "teléfono inteligente",
        "telefono inteligente",
    )

    accessory_signals = set(SMARTPHONE_ACCESSORY_TERMS) | {
        "lente",
        "lens",
        "objetivo",
        "macro lens",
        "wide angle lens",
        "teleobjetivo",
        "trípode",
        "tripode",
        "selfie stick",
        "palo selfie",
        "filtro cpl",
        "kit de lentes",
        "flash para",
        "estabilizador",
        "gimbal",
        "mango lateral",
        "jaula para",
        "soporte de vídeo",
        "soporte de video",
        "cargador",
        "cargador inalámbrico",
        "cable",
        "soporte para teléfono",
        "soporte para movil",
        "soporte para móvil",
        "funda",
        "carcasa",
    }

    return bool(
        any(term in text for term in device_terms)
        and not any(term in text for term in accessory_signals)
    )


HIGH_RISK_CATEGORIES = {
    "smartphones",
    "tablets",
    "laptops",
    "desktops",
    "cpu",
    "motherboards",
    "components",
    "monitors",
    "televisores",
    "cameras",
    "projectors",
    "drones",
}


@dataclass(frozen=True)
class SelectionDecision:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_eligibility(offer, score, classification):
    reasons = []

    normalized_title = " ".join(
        (getattr(offer, "title", "") or "").lower().split()
    )

    if getattr(offer, "category", None) in TECH_BLOCKED_CATEGORIES:
        reasons.append("categoria_excluida_de_tech")
    elif normalized_title:
        if not _tech_title_is_allowed(normalized_title):
            reasons.append("producto_fuera_de_tech")
        elif not _tech_category_title_is_allowed(
            getattr(offer, "category", None),
            normalized_title,
        ):
            reasons.append("familia_titulo_incoherente")

    if is_seasonally_premature(normalized_title):
        reasons.append("temporada_futura")

    if any(term in normalized_title for term in BLOCKED_PRODUCT_TERMS):
        reasons.append("tipo_producto_bloqueado")

    if _looks_like_replacement_part(normalized_title):
        reasons.append("pieza_repuesto_bajo_interes_editorial")
    elif _looks_like_low_interest_tech_item(normalized_title):
        reasons.append("producto_tecnico_de_bajo_interes_editorial")

    if (
        getattr(offer, "category", None) == "smartphones"
        and not _smartphone_is_real_product(normalized_title)
    ):
        reasons.append("smartphone_no_es_terminal")

    discount = offer.discount_pct or 0

    if discount < MIN_DISCOUNT_PCT:
        reasons.append(f"descuento<{MIN_DISCOUNT_PCT:.0f}%")

    if offer.rating is None or offer.rating < MIN_RATING:
        reasons.append(f"rating<{MIN_RATING:.1f}")

    reviews = offer.reviews

    if reviews is None:
        reasons.append("reseñas_desconocidas")
    elif reviews < MIN_REVIEWS:
        reasons.append(f"reseñas<{MIN_REVIEWS}")

        if offer.category in HIGH_RISK_CATEGORIES:
            reasons.append("categoria_de_riesgo_con_pocas_reseñas")

    if classification == "DESCARTAR":
        reasons.append("score_bajo")

    return SelectionDecision(
        not reasons,
        tuple(reasons),
    )


def _blocked_by_recent_publication(row):
    """
    Comprueba si la oferta está bloqueada por el guardián
    debido a una publicación reciente.

    Esta comprobación se realiza antes de aplicar
    MAX_PER_CATEGORY para evitar que una oferta que
    no puede publicarse consuma una plaza de su categoría.
    """

    score, offer, history, breakdown, classification = row

    product_id = getattr(offer, "product_id", None)

    # Si todavía no existe product_id, dejamos que el publisher
    # gestione posteriormente la situación y no bloqueamos aquí.
    if product_id is None:
        return False, "sin_product_id"

    blocked, reason = is_recent_duplicate(
        product_id=product_id,
        current_price=offer.current_price,
        current_discount_pct=offer.discount_pct,
        current_title=offer.title,
    )

    return blocked, reason


def _sort_for_diversity(scored_rows, recent_categories):
    """
    Ordena favoreciendo primero categorías no publicadas recientemente.
    Dentro de cada grupo manda el score.

    La diversidad no elimina ofertas buenas. Solo decide el orden en el
    que consumimos las plazas.
    """
    return sorted(
        scored_rows,
        key=lambda row: (
            -(
                1
                if (
                    getattr(row[1], "product_id", None) is not None
                    and recent_categories.get(
                        getattr(row[1], "category", None) or "uncategorized",
                        0,
                    )
                    == 0
                )
                else 0
            ),
            -int(bool(getattr(row[1], "brand", None) or extract_brand(getattr(row[1], "title", "")))),
            -CATEGORY_SELECTION_PRIORITY.get(
                getattr(row[1], "category", None) or "uncategorized",
                0,
            ),
            -row[0],
        ),
    )


def _row_is_publicable(row, relaxed=False):
    score, offer, history, breakdown, classification = row

    if PRIME_DAY_BROAD_MODE and offer.source != 'amazon':
        return False

    category = getattr(offer, "category", None)
    normalized_title = " ".join(
        (getattr(offer, "title", "") or "").lower().split()
    )

    # AhorroScan deja de exigir que cada publicación sea un chollo excepcional.
    # El filtro editorial conserva seguridad de categoría, producto y temporada,
    # pero abre la puerta a ofertas razonables y productos atractivos.
    relevance_score = getattr(offer, "relevance_score", None)
    if (
        getattr(offer, "source", "") == "aliexpress"
        and relevance_score is not None
        and not PRIME_DAY_BROAD_MODE
    ):
        min_relevance = 55.0 if relaxed else 70.0
        if relevance_score < min_relevance:
            return False

    history = row[2] if isinstance(row[2], dict) else {}
    history_count = int(history.get("count") or 0)
    history_average = history.get("average")
    if history_count >= 5 and history_average:
        required_drop = 0.02 if relaxed else 0.05
        if offer.current_price >= float(history_average) * (1.0 - required_drop):
            return False
    else:
        # Sin histórico suficiente, solo publicar ofertas con señales de confianza altas.
        if (offer.discount_pct or 0) < 20.0:
            return False
        if offer.rating is None or offer.rating < 4.2:
            return False
        if offer.reviews is None or offer.reviews < 20:
            return False

    min_score = (0.0 if PRIME_DAY_BROAD_MODE else (35.0 if relaxed else 45.0))
    min_discount = (MIN_DISCOUNT_PCT if PRIME_DAY_BROAD_MODE else (5.0 if relaxed else MIN_DISCOUNT_PCT))
    min_rating = (MIN_RATING if PRIME_DAY_BROAD_MODE else (3.5 if relaxed else MIN_RATING))
    min_reviews = (MIN_REVIEWS if PRIME_DAY_BROAD_MODE else (3 if relaxed else MIN_REVIEWS))

    if score < min_score:
        return False

    if (offer.discount_pct or 0) < min_discount:
        return False

    if offer.rating is None or offer.rating < min_rating:
        return False
    if PRIME_DAY_BROAD_MODE and offer.rating <= 4.3:
        return False

    if offer.reviews is None or offer.reviews < min_reviews:
        return False

    # En categorías de mayor riesgo de compra mantenemos un pequeño escalón
    # adicional de confianza, sin volver al embudo anterior.
    if category in HIGH_RISK_CATEGORIES:
        if offer.rating < 3.8 or offer.reviews < 10:
            return False

    if not _tech_title_is_allowed(normalized_title):
        return False

    if not _tech_category_title_is_allowed(category, normalized_title):
        return False

    if is_seasonally_premature(normalized_title):
        return False

    if any(term in normalized_title for term in BLOCKED_PRODUCT_TERMS):
        return False

    if _looks_like_replacement_part(normalized_title):
        return False

    if _looks_like_low_interest_tech_item(normalized_title):
        return False

    if (
        category == "smartphones"
        and not _smartphone_is_real_product(normalized_title)
    ):
        return False

    return True


def select_publicable(
    scored_rows,
    max_publicable=MAX_PUBLICABLE,
    max_per_category=MAX_PER_CATEGORY,
):
    selected = []
    counts = {}

    recent_categories = get_recent_category_counts(hours=18)
    audio_today = get_today_category_count("audio")

    ordered_rows = _sort_for_diversity(scored_rows, recent_categories)

    def build_eligible_rows(relaxed=False):
        result = []
        for row in ordered_rows:
            if not _row_is_publicable(row, relaxed=relaxed):
                continue
            recently_blocked, _ = _blocked_by_recent_publication(row)
            if recently_blocked:
                continue
            result.append(row)
        return result

    # Segundo pase únicamente cuando el filtro estricto no deja ninguna oferta.
    eligible_rows = build_eligible_rows(relaxed=False)
    if not eligible_rows:
        eligible_rows = build_eligible_rows(relaxed=True)

    # Pase 1: garantiza diversidad básica. Una oferta por categoría.
    for row in eligible_rows:
        category = row[1].category or "uncategorized"

        if category == "audio" and audio_today >= AUDIO_DAILY_LIMIT:
            continue

        if counts.get(category, 0) != 0:
            continue

        selected.append(row)
        counts[category] = 1

        if len(selected) >= max_publicable:
            return selected

    # Pase 2: rellenamos las plazas restantes por score.
    # Aquí permitimos una segunda oferta de una categoría, pero nunca una
    # tercera salvo que el caller haya pedido explícitamente max_per_category > 2.
    for row in eligible_rows:
        if row in selected:
            continue

        category = row[1].category or "uncategorized"

        if (
            category == "audio"
            and audio_today + counts.get("audio", 0) >= AUDIO_DAILY_LIMIT
        ):
            continue

        category_limit = CATEGORY_MAX_OVERRIDES.get(
            category,
            max_per_category,
        )

        if counts.get(category, 0) >= category_limit:
            continue

        selected.append(row)
        counts[category] = counts.get(category, 0) + 1

        if len(selected) >= max_publicable:
            break

    return selected
