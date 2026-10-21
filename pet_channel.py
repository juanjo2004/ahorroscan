from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta, timezone

from publication_guard import is_recent_duplicate
from prime_day import PRIME_DAY_MODE, prime_eligible

from dedupe import title_key
from product_relevance import is_repair_related

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "ofertas.db"

PET_TERMS = {
    "dog": ("perro", "perros", "canino", "canina", "puppy", "dog"),
    "cat": ("gato", "gatos", "felino", "felina", "kitten", "cat"),
    "pet_care": ("mascota", "mascotas", "cepillo mascota", "higiene mascota", "fuente agua"),
    "pet_accessories": ("correa", "arnes", "arnés", "collar", "transportin", "transportín", "comedero", "bebedero", "juguete mascota"),
    "aquarium": ("acuario", "pecera", "acuari", "filtro acuario", "peces", "fish tank"),
}

PET_BLOCKED = (
    "repuesto", "replacement", "pieza suelta", "miniatura", "juguete humano",
)

MIN_DISCOUNT_PCT = 8.0
MIN_RATING = 3.5
MIN_REVIEWS = 5
MAX_PUBLICABLE = 8
# Garantía de continuidad: si Mascotas lleva más de este tiempo sin publicar,
# se permite usar el fallback ya existente (sin relajar las reglas de repetición).
PET_CONTINUITY_HOURS = 6
_PET_SCHEMA_READY_PATH: str | None = None

def _text(value) -> str:
    return " ".join((value or "").lower().split())


_PET_FAMILY_STOPWORDS = {
    "para", "de", "del", "la", "el", "los", "las", "y", "con", "sin", "en", "por", "un", "una",
    "mascota", "mascotas", "producto", "productos", "suministros",
    "acuario", "pecera", "peces", "fish", "dog", "cat", "pet", "oferta", "nuevo", "nueva",
    "negro", "negra", "blanco", "blanca", "gris", "rojo", "roja", "azul", "verde", "rosa", "amarillo", "amarilla",
}


def _pet_family_key(title: str | None) -> str:
    """Normaliza variantes de un mismo producto/familia para el canal Mascotas."""
    text = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    text = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:cm|mm|m|l|ml|kg|g|w|v|a)\b", " ", text)
    text = re.sub(r"\b\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?\s*(?:cm|mm|m)?\b", " ", text)
    text = re.sub(r"\b(?:talla|tamano|tamaño|size|color)\s*[:=-]?\s*[a-z0-9]+\b", " ", text)
    text = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:unidades|unidad|uds?|piezas|pcs?)\b", " ", text)
    text = re.sub(r"\b(?:version|versión|edicion|edición|modelo|model)\s*[a-z0-9.-]+\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [t for t in text.split() if t not in _PET_FAMILY_STOPWORDS]
    return " ".join(tokens[:10])


def pet_kind(offer) -> str | None:
    text = _text(getattr(offer, "title", ""))
    if is_repair_related(text) or any(term in text for term in PET_BLOCKED):
        return None
    category = getattr(offer, "category", "") or ""
    if category in PET_TERMS and any(term in text for term in PET_TERMS[category]):
        return category
    for kind, terms in PET_TERMS.items():
        if any(term in text for term in terms):
            return kind
    return None


def pet_eligible(row) -> bool:
    score, offer, history, breakdown, classification = row
    if PRIME_DAY_MODE:
        return prime_eligible(score, offer, classification) and pet_kind(offer) is not None
    if classification == "DESCARTAR" and score < 45.0:
        return False
    if (offer.discount_pct or 0) < MIN_DISCOUNT_PCT:
        return False
    if offer.rating is None or offer.rating < MIN_RATING:
        return False
    if offer.reviews is None or offer.reviews < MIN_REVIEWS:
        return False
    return pet_kind(offer) is not None

def is_recent_pet_duplicate(product_id: int | None, current_title: str | None = None, current_price: float | None = None, current_discount_pct: float | None = None) -> tuple[bool, str]:
    """Aplica a Mascotas la misma ventana de repetición que los canales verticales: 7 días."""
    if product_id is None and not current_title:
        return False, "sin_identidad"

    init_pet_publications()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        if current_title:
            key = title_key(current_title)
            if key:
                rows = conn.execute(
                    "SELECT title FROM pet_publications WHERE datetime(published_at) >= datetime(?)",
                    (cutoff,),
                ).fetchall()
                if any(title_key(r["title"]) == key for r in rows):
                    return True, "titulo_duplicado_reciente"

        if product_id is not None:
            row = conn.execute(
                "SELECT published_at FROM pet_publications WHERE product_id=? ORDER BY datetime(published_at) DESC, id DESC LIMIT 1",
                (int(product_id),),
            ).fetchone()
            if row and row["published_at"]:
                published_dt = datetime.fromisoformat(
                    str(row["published_at"]).replace("Z", "+00:00")
                )
                if published_dt.tzinfo is None:
                    published_dt = published_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - published_dt < timedelta(days=7):
                    return True, "publicado_hace_menos_de_7_dias"

    if product_id is not None and current_price is not None:
        blocked, reason = is_recent_duplicate(
            product_id=int(product_id),
            current_price=float(current_price),
            current_discount_pct=current_discount_pct,
            current_title=current_title,
        )
        if blocked:
            return True, reason

    return False, "sin_repeticion_reciente"

def claim_pet_publication(product_id: int, title: str) -> bool:
    """Reserva atómicamente un producto antes de enviarlo a Telegram."""
    init_pet_publications()
    # Igual que los canales comunes: la reserva atómica se basa en el
    # título normalizado, no en la familia, para no bloquear variantes legítimas.
    key = title_key(title)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pet_publication_claims (
            product_id INTEGER PRIMARY KEY, title_key TEXT NOT NULL, claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        # Una reserva solo se elimina tras una publicación confirmada o un rechazo.
        # Si Telegram aceptó el mensaje pero el proceso cayó antes de registrarlo,
        # la reserva debe sobrevivir para impedir una republicación posterior.
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pet_publication_claims_family ON pet_publication_claims(title_key)")
        try:
            conn.execute("INSERT INTO pet_publication_claims(product_id,title_key) VALUES(?,?)", (int(product_id), key))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def release_pet_publication_claim(product_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM pet_publication_claims WHERE product_id=?", (int(product_id),))
        conn.commit()


def select_pet_publicable(scored_rows, max_publicable=MAX_PUBLICABLE):
    """Selecciona Mascotas con las mismas reglas base que los canales verticales."""
    selected = []
    used_categories = set()
    used_titles = set()

    for row in sorted(scored_rows, key=lambda item: item[0], reverse=True):
        score, offer, history, breakdown, classification = row

        if PRIME_DAY_MODE:
            if not pet_eligible(row):
                continue
        else:
            if classification == "DESCARTAR" and score < 45.0:
                continue
            if score < 45.0:
                continue
            if (offer.discount_pct or 0) < 8.0:
                continue
            if offer.rating is None or offer.rating < 3.5:
                continue
            if offer.reviews is None or offer.reviews < 5:
                continue
            if pet_kind(offer) is None:
                continue

        title_id = title_key(getattr(offer, "title", ""))
        if title_id and title_id in used_titles:
            continue

        product_id = getattr(offer, "product_id", None)
        blocked, _ = is_recent_pet_duplicate(
            product_id=product_id,
            current_title=getattr(offer, "title", None),
            current_price=getattr(offer, "current_price", None),
            current_discount_pct=getattr(offer, "discount_pct", None),
        )
        if blocked:
            continue

        kind = pet_kind(offer)
        if kind in used_categories:
            continue

        selected.append(row)
        used_categories.add(kind)
        if title_id:
            used_titles.add(title_id)

        if len(selected) >= max_publicable:
            return selected

    if PRIME_DAY_MODE:
        return selected[:max_publicable]

    for row in sorted(scored_rows, key=lambda item: item[0], reverse=True):
        if len(selected) >= max_publicable or row in selected:
            continue

        score, offer, history, breakdown, classification = row
        if classification == "DESCARTAR" and score < 45.0:
            continue
        if score < 45.0 or (offer.discount_pct or 0) < 8.0:
            continue
        if offer.rating is None or offer.rating < 3.5 or offer.reviews is None or offer.reviews < 5:
            continue
        if pet_kind(offer) is None:
            continue

        title_id = title_key(getattr(offer, "title", ""))
        if title_id and title_id in used_titles:
            continue

        product_id = getattr(offer, "product_id", None)
        blocked, _ = is_recent_pet_duplicate(
            product_id=product_id,
            current_title=getattr(offer, "title", None),
            current_price=getattr(offer, "current_price", None),
            current_discount_pct=getattr(offer, "discount_pct", None),
        )
        if blocked:
            continue

        selected.append(row)
        if title_id:
            used_titles.add(title_id)

    # Misma garantía de continuidad que los verticales: solo se relaja
    # descuento/score cuando hoy no existe ninguna publicación del canal.
    init_pet_publications()
    with sqlite3.connect(DB_PATH) as conn:
        today_count = conn.execute(
            "SELECT COUNT(*) FROM pet_publications WHERE substr(published_at,1,10)=date('now')"
        ).fetchone()[0]

    # La continuidad no debe depender de que el día UTC no tenga publicaciones:
    # una publicación a primera hora no puede dejar el canal mudo durante todo el día.
    latest_row = None
    with sqlite3.connect(DB_PATH) as conn:
        latest_row = conn.execute(
            "SELECT published_at FROM pet_publications ORDER BY datetime(published_at) DESC, id DESC LIMIT 1"
        ).fetchone()

    continuity_needed = latest_row is None
    if latest_row and latest_row[0]:
        try:
            latest_dt = datetime.fromisoformat(str(latest_row[0]).replace("Z", "+00:00"))
            if latest_dt.tzinfo is None:
                latest_dt = latest_dt.replace(tzinfo=timezone.utc)
            continuity_needed = datetime.now(timezone.utc) - latest_dt >= timedelta(hours=PET_CONTINUITY_HOURS)
        except (TypeError, ValueError):
            continuity_needed = True

    if not selected and continuity_needed:
        for row in sorted(scored_rows, key=lambda item: item[0], reverse=True):
            score, offer, history, breakdown, classification = row
            if pet_kind(offer) is None or score < 40.0 or (offer.discount_pct or 0) < 5.0:
                continue
            if offer.rating is None or offer.rating < 3.5 or offer.reviews is None or offer.reviews < 5:
                continue

            product_id = getattr(offer, "product_id", None)
            blocked, _ = is_recent_pet_duplicate(
                product_id=product_id,
                current_title=getattr(offer, "title", None),
                current_price=getattr(offer, "current_price", None),
                current_discount_pct=getattr(offer, "discount_pct", None),
            )
            if blocked:
                continue

            selected = [row]
            break

    return selected[:max_publicable]

def init_pet_publications():
    global _PET_SCHEMA_READY_PATH
    db_key = str(DB_PATH.resolve())
    if _PET_SCHEMA_READY_PATH == db_key:
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pet_publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,                price REAL,
                discount_pct REAL,
                score REAL,
                image_url TEXT,
                affiliate_url TEXT,
                telegram_message_id INTEGER,
                instagram_media_id TEXT,
                published_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pet_publication_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                external_id TEXT,
                title TEXT NOT NULL,
                telegram_message_id INTEGER,
                published_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pet_history_product_time ON pet_publication_history(product_id, published_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pet_history_source_external_time ON pet_publication_history(source, external_id, published_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pet_history_time ON pet_publication_history(published_at)")
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_pet_publications_history
            AFTER INSERT ON pet_publications
            BEGIN
                INSERT INTO pet_publication_history
                    (product_id, source, external_id, title, telegram_message_id, published_at)
                VALUES
                    (NEW.product_id, NEW.source, NEW.external_id, NEW.title, NEW.telegram_message_id, NEW.published_at);
            END
        """)
        conn.execute("""
            INSERT INTO pet_publication_history
                (product_id, source, external_id, title, telegram_message_id, published_at)
            SELECT p.product_id, p.source, p.external_id, p.title, p.telegram_message_id, p.published_at
            FROM pet_publications p
            WHERE NOT EXISTS (
                SELECT 1 FROM pet_publication_history h
                WHERE h.product_id=p.product_id AND h.published_at=p.published_at
            )
        """)
        conn.commit()
    _PET_SCHEMA_READY_PATH = db_key


def record_pet_publication(offer, score, telegram_message_id=None):
    """Registra cada publicación real y actualiza la fecha visible del producto.

    pet_publications conserva el estado actual del producto, mientras
    pet_publication_history conserva cada publicación individual. No se usa
    INSERT OR IGNORE porque eso dejaba publicada_at congelado en la primera
    publicación y permitía que el mismo producto volviera a salir.
    """
    init_pet_publications()
    published_at = datetime.now(timezone.utc).isoformat()
    product_id = int(getattr(offer, "product_id"))
    category = pet_kind(offer) or getattr(offer, "category", None) or "pet_care"

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT id FROM pet_publications WHERE product_id=? LIMIT 1",
            (product_id,),
        ).fetchone()

        if row:
            publication_id = int(row[0])
            conn.execute(
                """
                UPDATE pet_publications
                SET source=?, external_id=?, title=?, category=?, price=?,
                    discount_pct=?, score=?, image_url=?, affiliate_url=?,
                    telegram_message_id=?, published_at=?
                WHERE id=?
                """,
                (
                    offer.source, offer.external_id, offer.title, category,
                    offer.current_price, offer.discount_pct, score,
                    offer.image_url, offer.affiliate_url, telegram_message_id,
                    published_at, publication_id,
                ),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO pet_publications (
                    product_id, source, external_id, title, category, price,
                    discount_pct, score, image_url, affiliate_url,
                    telegram_message_id, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id, offer.source, offer.external_id, offer.title,
                    category, offer.current_price, offer.discount_pct, score,
                    offer.image_url, offer.affiliate_url, telegram_message_id,
                    published_at,
                ),
            )
            publication_id = int(cur.lastrowid)
        if row:
            # UPDATE no dispara el trigger de historial, por lo que esta
            # segunda publicación debe registrarse explícitamente.
            conn.execute(
                """
                INSERT INTO pet_publication_history (
                    product_id, source, external_id, title, telegram_message_id, published_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id, offer.source, offer.external_id, offer.title,
                    telegram_message_id, published_at,
                ),
            )
        conn.commit()
        return publication_id


def pet_web_offers(limit=24):
    init_pet_publications()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT product_id, source, external_id, title, category, price,
                   discount_pct, score, image_url, affiliate_url, published_at
            FROM pet_publications
            ORDER BY published_at DESC, id DESC
            LIMIT ?
        """, (max(1, min(int(limit), 50)),)).fetchall()
    return [dict(row) for row in rows]