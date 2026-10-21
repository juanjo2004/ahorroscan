import hashlib
import hmac
import json
import time
from pathlib import Path

import requests

from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID
from models import Offer
from aliexpress_classifier import RULE_BY_NAME, FUTURE_CATEGORY_TERMS, score_product


ENDPOINT = "https://api-sg.aliexpress.com/sync"
TOKEN_FILE = Path("data/aliexpress_token.json")
METHOD = "aliexpress.affiliate.product.query"
PARTNER_ID = "iop44-sdk-typescript-20231021"
LAST_STATUS = {"attempted": 0, "failed": 0, "api_errors": 0, "catalog_attempted": 0, "catalog_failed": 0}


def _refresh_access_token_once() -> bool:
    """Renueva OAuth una sola vez cuando AliExpress rechaza el access token."""
    try:
        from scripts.refresh_aliexpress_token_once import main as refresh_main
        refresh_main()
        return True
    except (SystemExit, Exception) as exc:
        print(f"[ALIEXPRESS] No se pudo renovar el token OAuth ({type(exc).__name__}).")
        return False


CATALOG_FIELDS = (
    "app_sale_price,app_sale_price_currency,commission_rate,discount,"
    "evaluate_rate,lastest_volume,original_price,original_price_currency,"
    "product_detail_url,product_id,product_main_image_url,product_title,"
    "promotion_link,sale_price,sale_price_currency,target_app_sale_price,"
    "target_original_price,target_sale_price,target_sale_price_currency,"
    "first_level_category_id,first_level_category_name,second_level_category_id"
)



def _fetch_catalog(method: str, extra: dict[str, str] | None = None) -> list[dict]:
    """Consulta fuentes del Centro de Anuncios usando la sesion afiliada."""
    LAST_STATUS["catalog_attempted"] += 1
    try:
        token = json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        token = None

    if not (ALI_APP_KEY and ALI_APP_SECRET and ALI_TRACKING_ID and token):
        LAST_STATUS["catalog_failed"] += 1
        return []

    params = {
        "app_key": str(ALI_APP_KEY),
        "session": str(token),
        "format": "json",
        "method": method,
        "partner_id": PARTNER_ID,
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0",
        "tracking_id": str(ALI_TRACKING_ID),
        "target_currency": "EUR",
        "target_language": "ES",
        "country": "ES",
        "page_no": "1",
        "page_size": "50",
        "fields": CATALOG_FIELDS,
    }
    if extra:
        params.update({k: str(v) for k, v in extra.items() if v not in (None, "")})
    params["sign"] = _sign(params, str(ALI_APP_SECRET))

    try:
        response = requests.post(
            ENDPOINT,
            data=params,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
        print(f"[ALIEXPRESS CATALOGO] HTTP {response.status_code} method={method}")
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        LAST_STATUS["catalog_failed"] += 1
        print(f"[ALIEXPRESS CATALOGO] Error: {exc}")
        return []

    if method.endswith("hotproduct.query"):
        response_key = "aliexpress_affiliate_hotproduct_query_response"
    else:
        response_key = "aliexpress_affiliate_featuredpromo_products_get_response"

    rr = data.get(response_key, {}).get("resp_result", {})
    if rr.get("resp_code") not in (None, 200, "200"):
        LAST_STATUS["catalog_failed"] += 1
        LAST_STATUS["api_errors"] += 1
        print(f"[ALIEXPRESS CATALOGO] API {rr.get('resp_code')}: {rr.get('resp_msg')}")
        return []

    products = rr.get("result", {}).get("products", {}).get("product", [])
    if isinstance(products, dict):
        products = [products]
    return products if isinstance(products, list) else []


def _promo_cache_path():
    return Path("data/aliexpress_promo_cache.json")


def get_centro_anuncios_promociones(force=False) -> list[dict]:
    """Obtiene y cachea los pools actuales del Centro de Anuncios."""
    cache_path = _promo_cache_path()
    now = time.time()
    if not force:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if now - float(cached.get("fetched_at", 0)) < 21600:
                return cached.get("promos", [])
        except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    LAST_STATUS["catalog_attempted"] += 1
    try:
        token = json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        token = None

    if not (ALI_APP_KEY and ALI_APP_SECRET and ALI_TRACKING_ID and token):
        LAST_STATUS["catalog_failed"] += 1
        return []

    params = {
        "app_key": str(ALI_APP_KEY),
        "session": str(token),
        "format": "json",
        "method": "aliexpress.affiliate.featuredpromo.get",
        "partner_id": PARTNER_ID,
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "v": "2.0",
        "tracking_id": str(ALI_TRACKING_ID),
    }
    params["sign"] = _sign(params, str(ALI_APP_SECRET))
    try:
        response = requests.post(
            ENDPOINT,
            data=params,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        LAST_STATUS["catalog_failed"] += 1
        print(f"[ALIEXPRESS CATALOGO] Promo info error: {exc}")
        return []

    rr = data.get("aliexpress_affiliate_featuredpromo_get_response", {}).get("resp_result", {})
    if rr.get("resp_code") not in (None, 200, "200"):
        LAST_STATUS["catalog_failed"] += 1
        LAST_STATUS["api_errors"] += 1
        print(f"[ALIEXPRESS CATALOGO] Promo API {rr.get('resp_code')}: {rr.get('resp_msg')}")
        return []

    promos = rr.get("result", {}).get("promos", [])
    if isinstance(promos, dict):
        promos = promos.get("promo", [])
    if not isinstance(promos, list):
        promos = []

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"fetched_at": now, "promos": promos}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return promos


CATALOG_TECH_NON_TECH_TERMS = (
    "lonchera", "fiambrera", "tupper", "tupperware", "contenedor de alimentos",
    "recipiente de comida", "bolsa térmica", "bolsa termica", "caja de almuerzo",
    "sartén", "sarten", "cacerola", "vajilla", "cubiertos", "mantel",
    "ropa", "camiseta", "camisa", "pantalón", "pantalon", "vestido", "zapatos",
    "zapatillas", "maquillaje", "cosmética", "cosmetica", "perfume", "juguete",
    "peluche", "joyería", "joyeria", "collar", "pulsera", "mascota", "perro", "gato",
)

CATALOG_BLOCKED_TERMS = (
    "funda", "case", "carcasa", "protector de pantalla", "screen protector",
    "cristal templado", "pegatina", "sticker", "cable", "adaptador",
    "adapter", "repuesto", "replacement", "accesorio", "accesorios",
    "correa", "strap", "estuche", "bolsa", "mochila", "alfombrilla",
    "mouse pad", "patines", "skates", "holder", "phone holder",
    "tablet holder", "laptop stand", "soporte para movil", "soporte para móvil",
    "replacement part", "spare part", "trípode", "tripode", "lente para", "objetivo para",
    "placa de bateria", "placa de batería", "disipador de calor", "resina",
    "filamento", "cabezal de impresión", "reposamuñecas", "almohadilla para teclado",
    "modulo de sensor", "módulo de sensor", "development board", "soporte universal",
    "soporte vertical", "soporte para computadora", "interruptores lineales", "keycaps",
    "teclas de pudín", "condensadores", "capacitores", "tuerca", "eje z",
    "luz de vídeo", "luz de video", "luz infrarroja", "herramienta de corrección",
)

CATALOG_CATEGORY_MAP = (
    ("gaming", ("8bitdo", "gamepad", "mando pc", "mando para pc", "controlador de juego", "gaming handheld", "steam deck", "consola")),
    ("smartphones", ("smartphone", "iphone", "movil", "móvil", "galaxy", "telefono movil", "teléfono móvil")),
    ("tablets", ("tablet", "ipad")),
    # No usamos "portátil" aislado como sinónimo de laptop: también aparece
    # constantemente en altavoces, luces, loncheras y otros productos.
    ("laptops", ("laptop", "portatil gaming", "portátil gaming", "ordenador portátil", "ordenador portatil", "pc portátil", "pc portatil", "computadora portátil", "computadora portatil", "notebook", "macbook")),
    ("desktops", ("mini pc", "mini pc", "desktop", "pc sobremesa", "all in one", "aio")),
    ("televisores", ("smart tv", "television", "televisión", "oled tv", "qled", "tv 4k")),
    ("cpu", ("ryzen", "intel core", "procesador", "cpu")),
    ("storage", ("ssd", "nvme", "disco duro", "hard drive")),
    ("monitors", ("monitor", "pantalla 144hz", "ultrawide")),
    ("audio", ("auriculares", "headphone", "earbuds", "altavoz", "soundbar", "speaker")),
    ("keyboards", ("teclado", "keyboard")),
    ("mice", ("raton", "ratón", "mouse")),
    ("networking", ("router", "wifi", "mesh", "switch ethernet", "access point")),
    ("charging", ("cargador", "charger", "gan", "power bank")),
    ("power", ("ups", "sai", "fuente de alimentacion", "fuente de alimentación")),
    ("wearables", ("smartwatch", "smart band", "smartband", "fitness tracker")),
    ("gaming", ("consola", "gamepad", "mando pc", "gaming handheld", "steam deck")),
    ("cameras", ("camara", "cámara", "dashcam", "action camera", "security camera", "camera body")),
    ("drones", ("drone", "dron", "quadcopter")),
    ("projectors", ("proyector", "projector")),
    ("vr", ("gafas vr", "vr headset", "virtual reality")),
    ("printers", ("impresora", "printer", "laser printer")),
    ("ereaders", ("ereader", "e-reader", "lector ebook")),
    ("smart_home", ("enchufe inteligente", "smart plug", "sensor inteligente", "smart home", "robot aspirador", "medidor de energia", "medidor de energía", "zigbee")),
    ("components", ("gpu", "tarjeta grafica", "tarjeta gráfica", "ram ddr5", "memoria ram", "placa base", "motherboard")),
    ("microphones", ("microfono", "micrófono", "microphone")),
)


def _contains_term(text: str, term: str) -> bool:
    import re
    return re.search(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", text) is not None


def _catalog_category(title: str, api_category: str = "") -> str | None:
    text = title.lower()

    # Filtro de primera línea para evitar que palabras ambiguas como
    # "portátil" clasifiquen productos cotidianos como tecnología.
    if any(term in text for term in CATALOG_TECH_NON_TECH_TERMS):
        return None

    # Un título puede mencionar "teléfono móvil" aunque el producto real
    # sea un accesorio (cargador, soporte, funda, etc.). En el Centro de
    # Anuncios no tenemos el clasificador de consultas productivas, así que
    # filtramos primero esos patrones para no contaminar smartphones.
    smartphone_accessory_phrases = (
        "cargador para", "cargador inalámbrico", "cargador de teléfono", "charger for", "cargador inalámbrico para", "wireless charger for",
        "soporte para", "support for", "holder for", "mount for", "stand for",
        "funda para", "case for", "carcasa para", "cover for", "protector para",
        "protector de pantalla", "screen protector", "cristal templado",
        "cable para", "cable for", "adaptador para", "adapter for",
        "batería de reemplazo", "replacement battery", "pantalla de reemplazo",
        "replacement screen", "repuesto para", "replacement for", "accesorio para",
        "accessory for", "soporte de vídeo para", "video rig for", "jaula para",
        "cage for", "mango para", "grip for", "trípode para", "tripod for",
        "stylus para", "lápiz óptico para", "gimbal para",
        "lente para", "lente de", "objetivo para", "macro lens", "wide angle lens",
        "lens for", "camera lens", "selfie stick", "palo selfie", "filtro cpl", "kit de lentes", "flash para",
    )
    smartphone_direct_terms = (
        "smartphone", "iphone", "galaxy", "telefono movil", "teléfono móvil",
        "teléfono inteligente", "telefono inteligente",
    )
    if any(term in text for term in smartphone_direct_terms) and any(
        phrase in text for phrase in smartphone_accessory_phrases
    ):
        smartphone_blocked = True
    else:
        smartphone_blocked = False

    # Guardas de producto accesorio: una mención a laptop/iPad/proyector no
    # convierte automáticamente un accesorio en el producto principal.
    accessory_blocks = {
        "laptops": ("ratón", "raton", "mouse", "lonchera", "bombilla", "bombillas",
                     "soporte para portátil", "soporte para laptop", "laptop stand",
                     "funda para portátil", "funda para laptop", "tapón antipolvo",
                     "radio portátil", "luz portátil", "cabezal de vídeo", "cabezal de video"),
        "tablets": ("puntas de lápiz", "puntas de lapiz", "lápiz óptico", "lapiz optico",
                    "stylus", "funda para ipad", "case for ipad", "protector de pantalla",
                    "ipad case", "tablet holder", "soporte para tablet"),
        "projectors": ("gafas 3d", "gafas 3D", "3d shutter glasses", "shutter glasses",
                       "head up display", "hud", "proyector de parabrisas",
                       "luz navideña", "luz navidena", "luz de halloween", "lámpara proyector", "lampara proyector"),
    }
    for category, blocked in accessory_blocks.items():
        if any(term.lower() in text for term in blocked):
            return None

    # Precedencia de familias con palabras inequívocas para evitar que un
    # "proyector portátil" acabe clasificado como portátil, etc.
    direct = (
        ("projectors", ("proyector", "projector")),
        ("monitors", ("monitor", "monitor gaming")),
        ("tablets", ("tablet", "ipad", "galaxy tab", "galaxy tablet")),
        ("smartphones", (
            "smartphone", "iphone", "galaxy", "redmi", "xiaomi", "poco", "pixel", "oneplus",
            "oppo", "realme", "motorola", "honor", "nothing", "vivo", "xperia", "tcl",
            "zte", "nubia", "asus", "zenfone", "rog phone", "nokia", "hmd", "doogee",
            "ulefone", "blackview", "fairphone", "telefono movil", "teléfono móvil",
            "teléfono inteligente", "telefono inteligente",
        )),
        ("printers", ("impresora", "printer")),
        ("drones", ("drone", "dron", "quadcopter")),
    )
    for category, terms in direct:
        if category == "smartphones" and smartphone_blocked:
            continue
        if any(_contains_term(text, term) for term in terms):
            return category
    # Storage debe tener prioridad sobre "laptop/portátil" cuando el producto
    # real es un SSD/NVMe destinado a un portátil.
    for category in ("storage",):
        terms = dict(CATALOG_CATEGORY_MAP).get(category, ())
        if any(_contains_term(text, term) for term in terms):
            return category
    for category, terms in CATALOG_CATEGORY_MAP:
        if category == "smartphones" and smartphone_blocked:
            continue
        if any(_contains_term(text, term) for term in terms):
            return category
    return None


def _promo_names_for_channel(channel="tech"):
    promos = get_centro_anuncios_promociones()
    names = [str(p.get("promo_name") or p.get("promotion_name") or "") for p in promos]
    if channel == "home":
        wanted = (
            "home", "kitchen", "garden", "furniture", "lighting", "tool",
            "house", "improvement", "garden", "home appliances",
        )
    else:
        wanted = (
            "tech", "computer", "electronics", "consumer", "electronic",
            "phone", "device", "newarrival", "newarrivals",
        )
    selected = [n for n in names if any(token in n.lower() for token in wanted)]
    priority = [
        "Fixed CPAi (tech Categories)",
        "DS_ConsumerElectronics_bestsellers",
        "DS_ElectronicComponents_bestsellers",
        "DS_NewArrivals",
        "ES_productos_cupones",
        "ES_products_coupons",
        "DS_Home&Kitchen_bestsellers",
        "AEB_US_Home&Garden_TopSellers",
        "AEB_US_Furniture_TopSellers",
        "AEB_Fetch_Garden&Tool&Pet&AutoParts_TopSellers_20241210",
    ]
    ordered = [n for n in priority if n in selected]
    ordered += [n for n in selected if n not in ordered]
    return ordered[:6]


def buscar_centro_anuncios(limite: int = 60, channel: str = "tech") -> list[Offer]:
    """Descubrimiento masivo desde Tendencias y pools tematicos del Centro de Anuncios."""
    raw = _fetch_catalog(
        "aliexpress.affiliate.hotproduct.query",
        {"sort": "volumeDesc"},
    )
    promotions = _promo_names_for_channel(channel)
    for promotion in promotions:
        raw.extend(
            _fetch_catalog(
                "aliexpress.affiliate.featuredpromo.products.get",
                {"promotion_name": promotion, "sort": "discountDesc"},
            )
        )

    offers = []
    seen = set()
    for item in raw:
        title = str(item.get("product_title") or "").strip()
        normalized_title = title.lower()
        if any(term in normalized_title for term in CATALOG_BLOCKED_TERMS):
            continue

        category = _catalog_category(
            title,
            str(item.get("first_level_category_name") or ""),
        )
        current = _to_float(
            item.get("target_sale_price")
            or item.get("app_sale_price")
            or item.get("sale_price")
        )
        reference = _to_float(
            item.get("target_original_price")
            or item.get("original_price")
        )
        rating = _to_rating(item.get("evaluate_rate"))
        volume = _to_int(item.get("lastest_volume"))
        url = str(item.get("product_detail_url") or "")
        affiliate = str(item.get("promotion_link") or "")

        if (
            not title
            or category is None
            or current is None
            or reference is None
            or reference <= current
            or not url.startswith("http")
            or not affiliate.startswith("http")
        ):
            continue

        discount = (reference - current) / reference * 100
        if discount < 7:
            continue
        if rating is not None and rating < 3.8:
            continue
        if volume is not None and volume < 10:
            continue

        key = str(item.get("product_id") or url)
        if key in seen:
            continue
        seen.add(key)

        offers.append(
            Offer(
                source="aliexpress",
                external_id=key,
                title=title,
                current_price=current,
                reference_price=reference,
                url=url,
                affiliate_url=affiliate,
                image_url=item.get("product_main_image_url") or None,
                rating=rating,
                reviews=volume,
                category=category,
            )
        )
        if len(offers) >= int(limite):
            break

    print(f"[ALIEXPRESS CATALOGO] Centro {channel}: {len(offers)} candidatas")
    return offers


def get_last_status():
    return dict(LAST_STATUS)



# Familias ya validadas experimentalmente.
CATEGORY_RULES = {
    "mice": "raton_gaming",
    "storage": "ssd_nvme",
    "monitors": "monitor_4k",
    "audio": "auriculares_bluetooth",
    "charging": "cargador_gan",
    "microphones": "microfono_usb",
}


# Consultas del catálogo que todavía no tienen una familia
# productiva validada en AliExpress.
DISABLED_QUERIES = {
    "disco duro externo ssd",
    "barra de sonido",
    "cargador usb c",
    "microfono streaming",
}


def _sign(params: dict[str, str], secret: str) -> str:
    canonical = "".join(
        k + str(params[k])
        for k in sorted(params)
        if params[k] not in (None, "")
    )

    return hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


def _to_float(value):
    if value is None or value == "":
        return None

    try:
        return float(
            str(value)
            .replace(",", ".")
            .strip()
            .replace("%", "")
        )
    except (TypeError, ValueError):
        return None


def _to_rating(value):
    v = _to_float(value)

    if v is None:
        return None

    # AliExpress devuelve normalmente evaluate_rate como porcentaje.
    if v > 5:
        v = v / 20.0

    return (
        round(v, 2)
        if 0 <= v <= 5
        else None
    )


def _to_int(value):
    if value is None or value == "":
        return None

    text = (
        str(value)
        .strip()
        .lower()
        .replace(" ", "")
    )

    try:
        if text.endswith("k"):
            return int(
                round(
                    float(
                        text[:-1]
                        .replace(",", ".")
                    )
                    * 1000
                )
            )

        if text.endswith("m"):
            return int(
                round(
                    float(
                        text[:-1]
                        .replace(",", ".")
                    )
                    * 1_000_000
                )
            )

        return int(
            float(
                text.replace(",", ".")
            )
        )

    except (TypeError, ValueError):
        return None


def _fetch(
    keyword: str,
    page_size: int = 20,
    _retried_after_refresh: bool = False,
) -> list[dict]:
    LAST_STATUS["attempted"] += 1
    app_key = ALI_APP_KEY
    app_secret = ALI_APP_SECRET
    tracking_id = ALI_TRACKING_ID

    if not (
        app_key
        and app_secret
        and tracking_id
    ):
        print(
            "[ALIEXPRESS] Credenciales/Tracking ID "
            "no configurados. Se omite."
        )
        LAST_STATUS["failed"] += 1
        return []

    try:
        token = json.loads(
            TOKEN_FILE.read_text(
                encoding="utf-8"
            )
        ).get("access_token")

    except (
        FileNotFoundError,
        json.JSONDecodeError,
        OSError,
    ):
        token = None

    if not token:
        print(
            "[ALIEXPRESS] Falta access_token. Se omite."
        )
        LAST_STATUS["failed"] += 1
        return []

    params = {
        "app_key": str(app_key),
        "session": token,
        "format": "json",
        "method": METHOD,
        "partner_id": PARTNER_ID,
        "sign_method": "sha256",
        "simplify": "false",
        "timestamp": str(
            int(
                time.time() * 1000
            )
        ),
        "v": "2.0",
        "keywords": keyword,
        "page_no": "1",
        "page_size": str(
            int(page_size)
        ),
        "tracking_id": str(tracking_id),
        "target_currency": "EUR",
        "target_language": "ES",
        "ship_to_country": "ES",
    }

    params["sign"] = _sign(
        params,
        str(app_secret),
    )

    try:
        r = requests.post(
            ENDPOINT,
            data=params,
            timeout=30,
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded;charset=utf-8"
            },
        )

        print(
            f"[ALIEXPRESS] HTTP {r.status_code} "
            f"para '{keyword}'"
        )

        r.raise_for_status()

        data = r.json()

    except Exception as exc:
        print(
            f"[ALIEXPRESS] Error de consulta "
            f"'{keyword}': {exc}"
        )
        LAST_STATUS["failed"] += 1
        return []

    error_response = data.get("error_response")
    if isinstance(error_response, dict):
        error_code = str(error_response.get("code") or "")
        error_msg = str(error_response.get("msg") or "")
        if error_code == "IllegalAccessToken" and not _retried_after_refresh:
            print("[ALIEXPRESS] Access token expirado; intentando renovar OAuth y repetir consulta.")
            if _refresh_access_token_once():
                return _fetch(keyword, page_size, _retried_after_refresh=True)
        LAST_STATUS["failed"] += 1
        LAST_STATUS["api_errors"] += 1
        print(f"[ALIEXPRESS] Error API {error_code or 'unknown'} para '{keyword}': {error_msg}")
        return []

    rr = (
        data.get(
            "aliexpress_affiliate_product_query_response",
            {},
        )
        .get(
            "resp_result",
            {},
        )
    )

    if (
        isinstance(rr, dict)
        and rr.get("resp_code")
        not in (
            None,
            200,
            "200",
        )
    ):
        code = str(rr.get("resp_code"))
        msg = str(rr.get("resp_msg") or "")
        print(f"[ALIEXPRESS] API {code}: {msg}")
        # AliExpress usa 405 también para consultas válidas sin resultados.
        # No debe degradar toda la fuente cuando el propio mensaje indica
        # explícitamente que el resultado está vacío.
        if code == "405" and "empty" in msg.lower():
            return []
        LAST_STATUS["failed"] += 1
        LAST_STATUS["api_errors"] += 1
        return []

    result = (
        rr.get("result", {})
        if isinstance(rr, dict)
        else {}
    )

    products = (
        result.get(
            "products",
            {},
        ).get(
            "product",
            [],
        )
        if isinstance(result, dict)
        else []
    )

    if isinstance(products, dict):
        products = [products]

    if not products:
        print(
            "[ALIEXPRESS DIAG API] "
            f"root_keys={list(data.keys())[:8]} error_response={data.get('error_response', {})} "
            f"rr_keys={list(rr.keys())[:8] if isinstance(rr, dict) else []} "
            f"code={rr.get('resp_code') if isinstance(rr, dict) else None} "
            f"msg={rr.get('resp_msg') if isinstance(rr, dict) else None} "
            f"result_type={type(result).__name__} "
            f"result_keys={list(result.keys())[:8] if isinstance(result, dict) else []}"
        )

    return (
        products
        if isinstance(products, list)
        else []
    )


def _rule_for(
    category: str | None,
    keywords: str,
) -> str | None:
    category = (
        category or ""
    ).strip().lower()

    q = (
        keywords or ""
    ).strip().lower()

    # Consultas explícitamente desactivadas.
    if q in DISABLED_QUERIES:
        return None

    # ============================================================
    # NUEVAS FAMILIAS VALIDADAS
    # ============================================================

    if (
        category == "audio"
        and q == "auriculares bluetooth"
    ):
        return "auriculares_bluetooth"

    if (
        category == "charging"
        and q == "cargador gan"
    ):
        return "cargador_gan"

    if (
        category == "microphones"
        and q == "microfono usb"
    ):
        return "microfono_usb"

    if category == "smartphones" and q in {
        "movil 5g", "movil 4g", "telefonos moviles", "telefonos moviles 5g", "xiaomi movil", "redmi smartphone", "poco smartphone", "smartphone 5g", "smartphone 4g",
        "telefono movil", "telefono android", "smartphone barato", "movil barato",
        "gama media smartphone", "gama alta smartphone", "iphone", "google pixel", "samsung galaxy",
        "xiaomi redmi poco", "motorola smartphone", "honor smartphone", "oppo realme",
        "oneplus nothing phone", "vivo smartphone", "sony xperia", "tcl smartphone",
        "zte nubia", "asus zenfone rog phone", "nokia hmd smartphone", "doogee ulefone blackview",
    }:
        return "smartphone_discovery"

    if category == "monitors" and q in {"monitor 27 144hz", "monitor 27 180hz", "monitor 24 144hz"}:
        return "monitor_gaming"

    # ============================================================
    # FAMILIAS FUTURAS: recolección histórica, sin publicación
    # ============================================================
    if category in FUTURE_CATEGORY_TERMS:
        rule_name = f"future_{category}"
        if rule_name in RULE_BY_NAME:
            return rule_name

    # ============================================================
    # REGLAS ANTERIORES
    # ============================================================

    if category in (
        "mice",
        "storage",
        "monitors",
    ):
        return CATEGORY_RULES.get(
            category
        )

    if category == "peripherals":
        if any(
            x in q
            for x in (
                "teclado",
                "keyboard",
            )
        ):
            return "teclado_mecanico"

        if any(
            x in q
            for x in (
                "raton",
                "mouse",
            )
        ):
            return "raton_gaming"

    return None


def _production_queries(
    rule_name: str,
    requested_query: str | None = None,
) -> tuple[str, ...]:
    rule = RULE_BY_NAME[rule_name]
    # La consulta de marca/modelo que emitió el catálogo debe llegar a la API
    # en todas las familias. Antes se sustituía por las consultas genéricas de la
    # regla, reduciendo el descubrimiento real. Se conserva el respaldo y deduplica.
    if requested_query and requested_query not in rule.queries:
        # Consultas específicas de marca/modelo deben aislarse. Mezclarlas con
        # aliases genéricos permitía que resultados genéricos superasen el score
        # aunque no correspondieran a la marca pedida. Los aliases se buscan
        # por separado desde el catálogo y siguen teniendo cobertura propia.
        return (requested_query,)
    if requested_query:
        return tuple(dict.fromkeys((requested_query, *rule.queries)))
    return rule.queries


def buscar(
    keywords="keyboard",
    limite=5,
    category=None,
):
    LAST_STATUS["attempted"] = 0
    LAST_STATUS["failed"] = 0
    LAST_STATUS["api_errors"] = 0
    rule_name = _rule_for(
        category,
        keywords,
    )

    if rule_name is None:
        print(
            "[ALIEXPRESS] V6.3 omite consulta "
            f"no validada: '{keywords}' "
            f"({category or '-'})"
        )
        return []

    rule = RULE_BY_NAME[
        rule_name
    ]

    all_ranked: dict[
        str,
        tuple[int, dict, list[str]],
    ] = {}

    for query in _production_queries(
        rule_name, keywords
    ):
        products = _fetch(
            query,
            page_size=max(
                20,
                int(limite) * 4,
            ),
        )

        for product in products:
            relevance_score, reasons = score_product(
                product,
                rule,
                query,
            )

            external_id = str(
                product.get(
                    "product_id"
                )
                or product.get(
                    "product_detail_url"
                )
                or product.get(
                    "product_title",
                    "",
                )
            )

            existing = all_ranked.get(
                external_id
            )

            if (
                existing is None
                or relevance_score > existing[0]
            ):
                all_ranked[
                    external_id
                ] = (
                    relevance_score,
                    product,
                    reasons,
                )

    ranked = sorted(
        all_ranked.values(),
        key=lambda x: x[0],
        reverse=True,
    )

    out: list[Offer] = []

    for (
        relevance_score,
        item,
        reasons,
    ) in ranked:

        # Las familias futuras están en fase de construcción de histórico.
        # Guardamos candidatos razonablemente relevantes aunque todavía no
        # alcancen el umbral editorial de producción (70). Nunca publican.
        # Recogemos candidatos desde 55; el selector aplica 70 en su pase
        # estricto y 55 en el pase de respaldo si no encuentra ofertas válidas.
        min_relevance = 40 if rule_name.startswith("future_") else 55
        if relevance_score < min_relevance:
            continue

        current = _to_float(
            item.get(
                "target_sale_price"
            )
            or item.get(
                "sale_price"
            )
            or item.get(
                "app_sale_price"
            )
        )

        reference = _to_float(
            item.get(
                "target_original_price"
            )
            or item.get(
                "original_price"
            )
        )

        if (
            current is None
            or reference is None
            or reference <= current
        ):
            continue

        title = item.get(
            "product_title",
            "Producto AliExpress",
        )

        image = (
            item.get(
                "product_main_image_url"
            )
            or ""
        )

        if image.startswith("//"):
            image = "https:" + image

        url = item.get(
            "product_detail_url",
            "",
        )

        affiliate = (
            item.get(
                "promotion_link"
            )
            or url
        )

        external_id = str(
            item.get(
                "product_id"
            )
            or url
            or title
        )

        offer = Offer(
            source="aliexpress",
            external_id=external_id,
            title=title,
            current_price=current,
            reference_price=reference,
            url=url,
            affiliate_url=affiliate,
            image_url=image or None,
            rating=_to_rating(item.get("evaluate_rate")),
            reviews=_to_int(item.get("lastest_volume")),
            category=category,
        )
        offer.relevance_score = relevance_score
        out.append(offer)

        if len(out) >= int(limite):
            break

    print(
        f"[ALIEXPRESS] V6.3 '{keywords}' "
        f"-> regla={rule_name} "
        f"-> {len(out)} productos válidos"
    )
    if not out:
        score55 = sum(1 for score, _item, _reasons in ranked if score >= 55)
        price_link_valid = 0
        for _score, item, _reasons in ranked:
            current_check = _to_float(item.get("target_sale_price") or item.get("sale_price") or item.get("app_sale_price"))
            reference_check = _to_float(item.get("target_original_price") or item.get("original_price"))
            url_check = item.get("product_detail_url") or ""
            affiliate_check = item.get("promotion_link") or url_check
            if current_check is not None and reference_check is not None and reference_check > current_check and url_check and affiliate_check:
                price_link_valid += 1
        print(f"[ALIEXPRESS DIAG] raw={len(ranked)} score55+={score55} price_link_valid={price_link_valid} max_score={ranked[0][0] if ranked else 'none'}")

    return out
