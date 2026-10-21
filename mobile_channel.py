from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from product_relevance import is_repair_related
from prime_day import PRIME_DAY_MODE, prime_eligible


MOBILE_REPEAT_BLOCK_DAYS = 7
MOBILE_FAMILY_REPEAT_BLOCK_DAYS = 7

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "ofertas.db"

MOBILE_PHONE_TERMS = (
    "smartphone", "iphone", "galaxy", "redmi", "xiaomi", "poco",
    "pixel", "oneplus", "oppo", "realme", "motorola", "honor",
    "nothing phone", "telefono movil", "teléfono móvil",
    "telefono inteligente", "teléfono inteligente",
)

MOBILE_ACCESSORY_TERMS = (
    "cargador", "charger", "funda", "case", "cover", "protector",
    "cristal templado", "screen protector", "cable usb", "cable tipo c",
    "usb c", "soporte movil", "soporte para movil", "power bank",
    "bateria externa", "batería externa", "cargador inalambrico",
    "cargador inalámbrico", "adaptador usb",
)

ACCESSORY_BLOCKED = (
    "repuesto", "replacement", "pantalla de reemplazo",
    "replacement screen", "carcasa vacia", "dummy phone",
    "filtro de lente", "kit de filtro", "lente de cámara", "lente de camara",
    "camera lens", "lens filter", "kit de lentes", "gimbal",
    "trípode", "tripode", "camera cage",)

MIN_DISCOUNT_PCT = 5.0
MIN_RATING = 3.5
MIN_REVIEWS = 5
FALLBACK_MIN_DISCOUNT_PCT = 3.0
FALLBACK_MIN_RATING = 3.2
FALLBACK_MIN_REVIEWS = 3
MAX_PUBLICABLE = 6
MAX_DAILY_PUBLICATIONS = int(__import__("os").getenv("MOVILES_MAX_DAILY_PUBLICATIONS", "8"))
MIN_DAILY_PUBLICATIONS = 1
PHONE_TARGET_PCT = 0.80
ACCESSORY_TARGET_PCT = 0.20


def _text(value) -> str:
    return " ".join((value or "").lower().split())


def is_phone_offer(offer) -> bool:
    text = _text(getattr(offer, "title", ""))
    return any(term in text for term in MOBILE_PHONE_TERMS) and not any(
        term in text for term in ACCESSORY_BLOCKED + MOBILE_ACCESSORY_TERMS
    )


def is_accessory_offer(offer) -> bool:
    text = _text(getattr(offer, "title", ""))
    return any(term in text for term in MOBILE_ACCESSORY_TERMS) and not any(
        term in text for term in ACCESSORY_BLOCKED
    )

def mobile_kind(offer) -> str | None:
    if is_repair_related(getattr(offer, "title", "")):
        return None
    if is_phone_offer(offer):
        return "smartphones"
    if is_accessory_offer(offer):
        return "mobile_accessories"
    return None


def _normalized_title_key(value) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", value or "").lower()
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def mobile_recently_published(product_id=None, source=None, external_id=None, title=None):
    """Return True when any stable identity for this offer was published recently."""
    if product_id is None and not (source and external_id) and not title:
        return False

    init_mobile_publications()
    cutoff = datetime.now(timezone.utc) - timedelta(days=MOBILE_REPEAT_BLOCK_DAYS)
    title_key = _normalized_title_key(title)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT product_id, source, external_id, title, published_at
            FROM mobile_publications
            WHERE datetime(published_at) >= datetime(?)
            ORDER BY published_at DESC, id DESC
            """,
            (cutoff.isoformat(),),
        ).fetchall()

    wanted_source = (source or "").strip().lower()
    wanted_external_id = str(external_id or "").strip()
    wanted_product_id = int(product_id) if product_id is not None else None

    for row in rows:
        row_product_id, row_source, row_external_id, row_title, published_at = row
        if not published_at:
            continue

        if wanted_product_id is not None and row_product_id == wanted_product_id:
            return True
        if (
            wanted_source
            and wanted_external_id
            and (row_source or "").strip().lower() == wanted_source
            and str(row_external_id or "").strip() == wanted_external_id
        ):
            return True
        if title_key and _normalized_title_key(row_title) == title_key:
            return True

    return False


def mobile_eligible(row, relaxed=False) -> bool:
    score, offer, history, breakdown, classification = row
    if PRIME_DAY_MODE:
        return prime_eligible(score, offer, classification) and mobile_kind(offer) is not None
    if getattr(offer, "source", "") == "aliexpress":
        # Ampliar descubrimiento de móviles AliExpress sin relajar el control de producto real.
        # Umbral moderado para ampliar móviles legítimos sin aceptar accesorios:
        # la clasificación final mobile_kind() sigue siendo obligatoria.
        min_relevance = 50.0
        if getattr(offer, "relevance_score", 0.0) < min_relevance:
            return False
    if classification == "DESCARTAR" and score < 45.0 and not relaxed:
        return False
    history_count = int(history.get("count") or 0) if isinstance(history, dict) else 0
    history_average = history.get("average") if isinstance(history, dict) else None
    if history_count >= 5 and history_average:
        required_drop = 0.02 if relaxed else 0.05
        if offer.current_price >= float(history_average) * (1.0 - required_drop):
            return False
    else:
        # Sin histórico, solo se acepta una oferta con descuento y confianza sólidos.
        min_discount_without_history = 7.0 if getattr(offer, "source", "") == "aliexpress" else 20.0
        min_rating_without_history = 4.0 if getattr(offer, "source", "") == "aliexpress" else 4.2
        min_reviews_without_history = 10 if getattr(offer, "source", "") == "aliexpress" else 20
        if (offer.discount_pct or 0) < min_discount_without_history:
            return False
        if offer.rating is None or offer.rating < min_rating_without_history:
            return False
        if offer.reviews is None or offer.reviews < min_reviews_without_history:
            return False

    min_score = 35.0 if relaxed else 40.0
    min_discount = FALLBACK_MIN_DISCOUNT_PCT if relaxed else MIN_DISCOUNT_PCT
    min_rating = FALLBACK_MIN_RATING if relaxed else MIN_RATING
    min_reviews = FALLBACK_MIN_REVIEWS if relaxed else MIN_REVIEWS
    if score < min_score:
        return False
    if (offer.discount_pct or 0) < min_discount:
        return False
    if offer.rating is None or offer.rating < min_rating:
        return False
    if offer.reviews is None or offer.reviews < min_reviews:
        return False
    return mobile_kind(offer) is not None


def _mobile_family_key(offer):
    """Normaliza un móvil a familia/modelo para evitar variantes repetidas."""
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", getattr(offer, "title", "") or "").lower()
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\([^)]*\)", " ", text)

    # Elimina ruido que diferencia variantes pero no cambia el modelo.
    text = re.sub(
        r"\b(?:negro|negra|blanco|blanca|azul|rojo|roja|verde|amarillo|amarilla|"
        r"rosa|rosado|violeta|lavanda|cobalto|grafito|grafite|obsidiana|"
        r"frambuesa|turquesa|cereza oscuro|gris niebla|gris|dorado|oro|plateado|"
        r"morado|plata|carbon|carbono|midnight|navy|sky blue)\b", " ", text)
    text = re.sub(
        r"\b(?:\d+(?:\.\d+)?\s*(?:gb|tb|g|mah|w)|\d+\+\d+(?:gb|tb)?|"
        r"\d+/\d+(?:gb|tb)?|\d+x\d+(?:gb|tb)?)\b", " ", text)
    text = re.sub(r"\b(?:5g|4g|dual sim|single sim|version espanola|version espanol)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = " ".join(text.split())

    # Identidad fuerte de familia. Si no podemos identificarla, devolvemos
    # el título normalizado para conservar el guardián exacto existente.
    brands = (
        "apple", "iphone", "samsung", "galaxy", "xiaomi", "redmi", "poco",
        "google", "pixel", "motorola", "moto", "honor", "oppo", "realme",
        "oneplus", "nothing", "vivo", "sony", "xperia", "tcl", "zte",
        "nubia", "asus", "zenfone", "rog phone", "nokia", "hmd",
        "doogee", "ulefone", "blackview", "fairphone",
    )
    tokens = text.split()
    if not tokens:
        return ""

    # Conserva las primeras piezas relevantes del nombre comercial, evitando
    # que cámara/batería/pantalla creen familias distintas para el mismo modelo.
    brand_index = next((i for i,t in enumerate(tokens) if t in brands), None)
    if brand_index is None:
        return text

    family_tokens = tokens[brand_index:]
    stop = {
        "smartphone", "telefono", "movil", "mobile", "android", "con", "para",
        "camara", "camera", "bateria", "pantalla", "carga", "rapida", "ram",
        "memoria", "garantia", "fabricante", "nuevo", "reacondicionado",
    }
    kept=[]
    for tok in family_tokens:
        if tok in stop and len(kept) >= 2:
            break
        kept.append(tok)
        if len(kept) >= 5:
            break
    return " ".join(kept)


def _mobile_brand_key(offer):
    import re
    text = _text(getattr(offer, "title", ""))
    for brand in (
        "samsung", "xiaomi", "redmi", "poco", "apple", "iphone", "google",
        "pixel", "motorola", "honor", "oppo", "realme", "oneplus", "nothing",
        "vivo", "sony", "tcl", "zte", "nubia", "asus", "nokia", "hmd",
        "doogee", "ulefone", "blackview", "fairphone",
    ):
        if re.search(rf"\b{re.escape(brand)}\b", text):
            return brand
    return "unknown"


def _recent_mobile_family_counts(conn, days=MOBILE_FAMILY_REPEAT_BLOCK_DAYS):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = conn.execute(
        """
        SELECT title FROM mobile_publications
        WHERE datetime(published_at) >= datetime(?)
        """,
        (cutoff.isoformat(),),
    ).fetchall()
    families = {}
    brands = {}
    for (title,) in rows:
        class _Offer: pass
        offer = _Offer()
        offer.title = title
        family = _mobile_family_key(offer)
        brand = _mobile_brand_key(offer)
        if family:
            families[family] = families.get(family, 0) + 1
        brands[brand] = brands.get(brand, 0) + 1
    return families, brands


def select_mobile_publicable(scored_rows, max_publicable=MAX_PUBLICABLE):
    """Selecciona Móviles priorizando variedad real sin romper el guardián exacto."""
    init_mobile_publications()
    with sqlite3.connect(DB_PATH) as conn:
        daily_published = conn.execute(
            "SELECT COUNT(*) FROM mobile_publications WHERE substr(published_at,1,10)=date('now')"
        ).fetchone()[0]
        recent_families, recent_brands = _recent_mobile_family_counts(conn)

    remaining_daily = max(0, MAX_DAILY_PUBLICATIONS - int(daily_published))
    if remaining_daily <= 0:
        return []
    max_publicable = min(max_publicable, remaining_daily)

    phones, accessories = [], []
    seen_titles = set()
    seen_families = set()
    seen_brands = set()

    ordered_rows = sorted(scored_rows, key=lambda item: item[0], reverse=True)

    def build_candidates(relaxed=False):
        result = []
        for row in ordered_rows:
            if not mobile_eligible(row, relaxed=relaxed):
                continue
            offer = row[1]
            title_key = _normalized_title_key(offer.title)
            if title_key and title_key in seen_titles:
                continue
            product_id = getattr(offer, "product_id", None)
            if product_id is not None and mobile_recently_published(
                product_id=product_id, source=offer.source,
                external_id=offer.external_id, title=offer.title
            ):
                continue
            result.append(row)
        return result

    # Solo flexibilizar si el filtro habitual no encuentra ninguna oferta.
    candidates = build_candidates(relaxed=False)
    if not candidates:
        candidates = build_candidates(relaxed=True)

    def rank(row):
        offer=row[1]
        kind=mobile_kind(offer)
        family=_mobile_family_key(offer) if kind == "smartphones" else ""
        brand=_mobile_brand_key(offer) if kind == "smartphones" else ""
        family_penalty=min(recent_families.get(family,0),2)
        brand_penalty=min(recent_brands.get(brand,0),2)
        return (family_penalty, brand_penalty, -row[0])

    candidates.sort(key=rank)
    fresh_phones=[]
    recent_phones=[]
    for row in candidates:
        offer=row[1]
        kind=mobile_kind(offer)
        title_key=_normalized_title_key(offer.title)
        if kind == "smartphones":
            family=_mobile_family_key(offer)
            if family and family in seen_families:
                continue
            if family and family in recent_families:
                recent_phones.append(row)
            else:
                fresh_phones.append(row)
            if title_key: seen_titles.add(title_key)
            if family: seen_families.add(family)
        elif kind == "mobile_accessories":
            accessories.append(row)
            if title_key: seen_titles.add(title_key)

    phone_target=round(max_publicable*PHONE_TARGET_PCT)
    accessory_target=max_publicable-phone_target
    # Durante 7 días no repetimos familia/modelo si existen otras familias
    # elegibles. El fallback solo entra cuando el mercado no ofrece suficiente
    # variedad real, evitando dejar el canal vacío.
    selected=fresh_phones[:phone_target]+accessories[:accessory_target]

    if len(selected)<max_publicable:
        remaining_fresh=[r for r in fresh_phones[phone_target:]+accessories[accessory_target:] if r not in selected]
        for row in remaining_fresh:
            if len(selected)>=max_publicable: break
            selected.append(row)

    if len(selected)<max_publicable:
        for row in recent_phones:
            if len(selected)>=max_publicable: break
            selected.append(row)

    if not selected and daily_published < MIN_DAILY_PUBLICATIONS:
        for row in candidates:
            if mobile_kind(row[1])=="smartphones":
                selected=[row]; break

    return selected[:max_publicable]


def init_mobile_publications():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mobile_publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL,
                discount_pct REAL,
                score REAL,
                image_url TEXT,
                affiliate_url TEXT,
                telegram_message_id INTEGER,
                instagram_media_id TEXT,
                published_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mobile_publications_product_published ON mobile_publications(product_id, published_at DESC, id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mobile_publications_published ON mobile_publications(published_at DESC, id DESC)")
        conn.commit()


def mobile_web_offers(limit=24):
    init_mobile_publications()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT product_id, source, external_id, title, category, price,
                   discount_pct, score, image_url, affiliate_url, published_at
            FROM mobile_publications
            ORDER BY published_at DESC, id DESC
            LIMIT ?
        """, (max(1, min(int(limit), 50)),)).fetchall()
    return [dict(row) for row in rows]
def record_mobile_publication(offer, score, telegram_message_id=None):
    init_mobile_publications()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("""
            INSERT INTO mobile_publications (
                product_id, source, external_id, title, category, price,
                discount_pct, score, image_url, affiliate_url, telegram_message_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (            getattr(offer, "product_id"),
            offer.source,
            offer.external_id,
            offer.title,
            mobile_kind(offer) or getattr(offer, "category", None) or "mobile_accessories",
            offer.current_price,
            offer.discount_pct,
            score,
            offer.image_url,
            offer.affiliate_url,
            telegram_message_id,
        ))
        conn.commit()
        return cur.lastrowid