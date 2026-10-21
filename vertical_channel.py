from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from publication_guard import is_recent_duplicate, title_key
from product_relevance import is_repair_related
from prime_day import PRIME_DAY_MODE, prime_eligible


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "ofertas.db"

# Un producto puede volver a aparecer en Moda/Deportes cuando hayan
# transcurrido al menos estos días desde su última publicación en ese canal.
VERTICAL_REPEAT_BLOCK_DAYS = 7

VERTICAL_BLOCKED_TERMS = {
    "smartwatch",
    "reloj inteligente",
    "smart band",
    "smartband",
    "fitness tracker",
    "smartphone",
    "iphone",
    "telefono movil",
    "teléfono móvil",
    "tablet",
    "ipad",
    "portatil",
    "portátil",
    "laptop",
    "monitor",
    "ssd",
    "nvme",
    "auricular",
    "headphone",
    "earbuds",
    "teclado",
    "keyboard",
    "raton gaming",
    "mouse gaming",
    "cargador usb",
    "power bank",
    # Moda: evitar disfraces/cosplay clasificados erróneamente como ropa diaria.
    "cosplay",
    "disfraz de anime",
    "disfraz de comic",
    "disfraz de cómic",
}


def vertical_title_allowed(channel, title):
    text = " ".join((title or "").lower().split())
    return not is_repair_related(text) and not any(
        term in text for term in VERTICAL_BLOCKED_TERMS
    )


def _configured_vertical_channels():
    """Build vertical channel policies from the shared registry and catalogs."""
    from channel_registry import channels as registered_channels

    catalog_path = Path(__file__).resolve().parent / "config" / "channel_catalogs.json"
    catalogs = json.loads(catalog_path.read_text(encoding="utf-8")).get("catalogs", {})
    specialized = {"tech", "hogar", "moviles", "mascotas"}
    configured = {}
    for channel_id, channel in registered_channels().items():
        if channel_id in specialized:
            continue
        catalog = catalogs.get(channel_id)
        if not isinstance(catalog, dict) or not catalog:
            continue
        chat_env = channel.get("telegram_env", "")
        prefix = chat_env.removesuffix("_TELEGRAM_CHAT_ID") or channel_id.upper()
        prefix = prefix.replace("-", "_")
        configured[channel_id] = {
            "family": channel.get("family", channel_id),
            "categories": list(catalog),
            "telegram_env": chat_env or f"{prefix}_TELEGRAM_CHAT_ID",
            "dry_env": channel.get("dry_env", f"{prefix}_TELEGRAM_DRY_RUN"),
            "max_env": channel.get("max_env", f"{prefix}_MAX_PUBLICATIONS_PER_RUN"),
            "labels": {key: key.replace("_", " ").upper() for key in catalog},
        }
    return configured


CHANNELS = _configured_vertical_channels()
_LAST_SELECTION_REJECTIONS = {}


def last_selection_rejections(channel):
    return dict(_LAST_SELECTION_REJECTIONS.get(channel, {}))


def select_vertical_publicable(scored_rows, channel, max_publicable=8):
    global _LAST_SELECTION_REJECTIONS
    cfg = CHANNELS[channel]
    if PRIME_DAY_MODE:
        selected = []
        used = set()
        used_titles = set()
        rejections = Counter()
        for row in sorted(scored_rows, key=lambda x: x[0], reverse=True):
            score, offer, history, breakdown, classification = row
            if not prime_eligible(score, offer, classification):
                rejections["prime_day_quality"] += 1
                continue
            if getattr(offer, "category", "") not in cfg["categories"]:
                rejections["category_outside_catalog"] += 1
                continue
            if not vertical_title_allowed(channel, getattr(offer, "title", "")):
                rejections["title_blocked_for_channel"] += 1
                continue
            title_id = title_key(getattr(offer, "title", ""))
            if title_id and title_id in used_titles:
                continue
            if already_published(channel, getattr(offer, "product_id", None), current_title=offer.title):
                rejections["recently_published_in_channel"] += 1
                continue
            pid = getattr(offer, "product_id", None)
            if pid is not None:
                blocked, _ = is_recent_duplicate(
                    product_id=pid,
                    current_price=offer.current_price,
                    current_discount_pct=offer.discount_pct,
                    current_title=offer.title,
                )
                if blocked:
                    rejections["recently_published_project_wide"] += 1
                    continue
            cat = offer.category
            if cat in used:
                rejections["category_diversity_cap"] += 1
                continue
            selected.append(row)
            used.add(cat)
            if title_id:
                used_titles.add(title_id)
            if len(selected) >= max_publicable:
                break
        _LAST_SELECTION_REJECTIONS[channel] = dict(sorted(rejections.items()))
        return selected
    rejections = Counter()
    selected = []
    used = set()
    used_titles = set()

    for row in sorted(scored_rows, key=lambda x: x[0], reverse=True):
        score, offer, history, breakdown, classification = row

        if classification == "DESCARTAR" and score < 45.0:
            rejections["score_below_45"] += 1
            continue
        if score < 45.0:
            rejections["score_below_45"] += 1
            continue
        if (offer.discount_pct or 0) < 8:
            rejections["discount_below_8_percent"] += 1
            continue
        if offer.rating is None:
            rejections["rating_missing"] += 1
            continue
        if offer.rating < 3.5:
            rejections["rating_below_3_5"] += 1
            continue
        if offer.reviews is None:
            rejections["reviews_missing"] += 1
            continue
        if offer.reviews < 5:
            rejections["reviews_below_5"] += 1
            continue
        if getattr(offer, "category", "") not in cfg["categories"]:
            rejections["category_outside_catalog"] += 1
            continue
        if not vertical_title_allowed(channel, getattr(offer, "title", "")):
            rejections["title_blocked_for_channel"] += 1
            continue

        title_id = title_key(getattr(offer, "title", ""))
        if title_id and title_id in used_titles:
            rejections["duplicate_title_in_cycle"] += 1
            continue
        if already_published(
            channel, getattr(offer, "product_id", None), current_title=offer.title
        ):
            rejections["recently_published_in_channel"] += 1
            continue

        pid = getattr(offer, "product_id", None)
        if pid is not None:
            blocked, _ = is_recent_duplicate(
                product_id=pid,
                current_price=offer.current_price,
                current_discount_pct=offer.discount_pct,
                current_title=offer.title,
            )
            if blocked:
                rejections["recently_published_project_wide"] += 1
                continue

        cat = offer.category
        if cat in used:
            rejections["category_diversity_cap"] += 1
            continue

        selected.append(row)
        used.add(cat)
        if title_id:
            used_titles.add(title_id)

        if len(selected) >= max_publicable:
            _LAST_SELECTION_REJECTIONS[channel] = dict(sorted(rejections.items()))
            return selected

    for row in sorted(scored_rows, key=lambda x: x[0], reverse=True):
        if len(selected) >= max_publicable or row in selected:
            continue

        score, offer, history, breakdown, classification = row

        if classification == "DESCARTAR" and score < 45.0:
            continue
        if score < 45.0 or (offer.discount_pct or 0) < 8:
            continue
        if (
            offer.rating is None
            or offer.rating < 3.5
            or offer.reviews is None
            or offer.reviews < 5
        ):
            continue
        if offer.category not in cfg["categories"]:
            continue
        if not vertical_title_allowed(channel, getattr(offer, "title", "")):
            continue

        title_id = title_key(getattr(offer, "title", ""))
        if title_id and title_id in used_titles:
            continue
        if already_published(
            channel, getattr(offer, "product_id", None), current_title=offer.title
        ):
            continue

        pid = getattr(offer, "product_id", None)
        if pid is not None:
            blocked, _ = is_recent_duplicate(
                product_id=pid,
                current_price=offer.current_price,
                current_discount_pct=offer.discount_pct,
                current_title=offer.title,
            )
            if blocked:
                continue

        selected.append(row)
        if title_id:
            used_titles.add(title_id)

    # Garantía de continuidad: si hoy no existe publicación del vertical,
    # usamos el mejor candidato razonable del propio canal como respaldo.
    table = _table(channel)

    with sqlite3.connect(DB_PATH) as c:
        today_count = c.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE substr(published_at, 1, 10) = date('now')
            """
        ).fetchone()[0]

    if not selected and today_count == 0:
        for row in sorted(scored_rows, key=lambda x: x[0], reverse=True):
            score, offer, history, breakdown, classification = row

            if (
                offer.category not in cfg["categories"]
                or score < 40.0
                or (offer.discount_pct or 0) < 5.0
            ):
                continue

            if not vertical_title_allowed(
                channel, getattr(offer, "title", "")
            ):
                continue

            if (
                offer.rating is None
                or offer.rating < 3.5
                or offer.reviews is None
                or offer.reviews < 5
            ):
                continue

            pid = getattr(offer, "product_id", None)
            if already_published(channel, pid, current_title=offer.title):
                continue

            if pid is not None:
                blocked, _ = is_recent_duplicate(
                    product_id=pid,
                    current_price=offer.current_price,
                    current_discount_pct=offer.discount_pct,
                    current_title=offer.title,
                )
                if blocked:
                    continue

            selected = [row]
            break

    _LAST_SELECTION_REJECTIONS[channel] = dict(sorted(rejections.items()))
    return selected[:max_publicable]


def _table(channel):
    """Keep current vertical history and give every added channel its own table."""
    legacy = {
        "moda": "fashion_publications",
        "deportes": "sports_publications",
    }
    if channel in legacy:
        return legacy[channel]
    if channel not in CHANNELS:
        raise ValueError(f"Canal vertical no registrado: {channel}")
    safe_channel = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in channel.lower())
    return f"vertical_{safe_channel}_publications"


def init_channel(channel):
    table = _table(channel)

    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
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
                rating REAL,
                reviews INTEGER,
                telegram_message_id INTEGER,
                published_at TEXT DEFAULT CURRENT_TIMESTAMP,
                origin TEXT NOT NULL DEFAULT 'tech',
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )

        c.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_product_published
            ON {table}(product_id, published_at DESC, id DESC)
            """
        )

        c.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table}_published
            ON {table}(published_at DESC, id DESC)
            """
        )

        c.commit()


def record_publication(channel, offer, score, telegram_message_id=None):
    init_channel(channel)
    table = _table(channel)

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            f"""
            INSERT INTO {table} (
                product_id,
                source,
                external_id,
                title,
                category,
                price,
                discount_pct,
                score,
                image_url,
                affiliate_url,
                rating,
                reviews,
                telegram_message_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                getattr(offer, "product_id"),
                offer.source,
                offer.external_id,
                offer.title,
                offer.category,
                offer.current_price,
                offer.discount_pct,
                score,
                offer.image_url,
                offer.affiliate_url,
                getattr(offer, "rating", None),
                getattr(offer, "reviews", None),
                telegram_message_id,
            ),
        )

        c.commit()
        return cur.lastrowid


def vertical_web_offers(channel, limit=24):
    init_channel(channel)
    table = _table(channel)

    with sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row

        rows = c.execute(
            f"""
            SELECT
                product_id,
                source,
                external_id,
                title,
                category,
                price,
                discount_pct,
                score,
                published_at,
                affiliate_url,
                image_url
            FROM {table}
            ORDER BY published_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 50)),),
        ).fetchall()

    return [dict(r) for r in rows]


def already_published(
    channel,
    product_id,
    current_price=None,
    current_discount_pct=None,
    current_title=None,
):
    """
    Devuelve True únicamente si el producto fue publicado recientemente
    en ESTE canal.

    La ventana de bloqueo es de VERTICAL_REPEAT_BLOCK_DAYS días.
    Una publicación anterior a esa ventana no bloquea una nueva publicación.
    """

    init_channel(channel)
    table = _table(channel)

    if current_title:
        current_key = title_key(current_title)
        if current_key:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=VERTICAL_REPEAT_BLOCK_DAYS)).isoformat()
            with sqlite3.connect(DB_PATH) as c:
                recent_titles = c.execute(
                    f"SELECT title FROM {table} WHERE datetime(published_at) >= datetime(?)",
                    (cutoff,),
                ).fetchall()
            if any(title_key(row[0]) == current_key for row in recent_titles):
                return True

    if product_id is None:
        return False

    with sqlite3.connect(DB_PATH) as c:
        row = c.execute(
            f"""
            SELECT published_at
            FROM {table}
            WHERE product_id = ?
            ORDER BY datetime(published_at) DESC, id DESC
            LIMIT 1
            """,
            (product_id,),
        ).fetchone()

    if not row or not row[0]:
        return False

    published_at = row[0]

    try:
        published_dt = datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        )

        if published_dt.tzinfo is None:
            published_dt = published_dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_seconds = (now - published_dt).total_seconds()

    except (TypeError, ValueError):
        # Ante una fecha histórica inválida no bloqueamos permanentemente
        # el producto. El publisher podrá registrar la nueva publicación.
        return False

    return age_seconds < VERTICAL_REPEAT_BLOCK_DAYS * 86400
