from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from dedupe import title_key

DB_PATH = Path(__file__).resolve().parent / "data" / "ofertas.db"

# Reglas de repetición
REPEAT_BLOCK_DAYS = 7
REPEAT_PRICE_IMPROVEMENT_PCT = 10.0
REPEAT_DISCOUNT_IMPROVEMENT_POINTS = 10.0
PUBLICATION_ORIGIN = "tech"

# Límites de seguridad de publicación
import config

MAX_PUBLICATIONS_PER_RUN = getattr(
    config,
    "MAX_PUBLICATIONS_PER_RUN",
    5,
)

MAX_PUBLICATIONS_PER_DAY = int(
    getattr(
        config,
        "MAX_PUBLICATIONS_PER_DAY",
        24,
    )
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "publications" in tables:
        columns = {r[1] for r in conn.execute("PRAGMA table_info(publications)")}
        if "origin" not in columns:
            conn.execute("ALTER TABLE publications ADD COLUMN origin TEXT NOT NULL DEFAULT 'tech'")
    if "publication_claims" in tables:
        columns = {r[1] for r in conn.execute("PRAGMA table_info(publication_claims)")}
        if "origin" not in columns:
            conn.execute("ALTER TABLE publication_claims ADD COLUMN origin TEXT NOT NULL DEFAULT 'tech'")
    return conn


def _title_key(value: str) -> str:
    import re, unicodedata
    text = unicodedata.normalize("NFKD", value or "").lower()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def init_atomic_publication_guard():
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS publication_claims (
            channel TEXT NOT NULL, product_id INTEGER NOT NULL, title_key TEXT NOT NULL,
            claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, origin TEXT NOT NULL DEFAULT 'tech',
            PRIMARY KEY(channel, product_id), UNIQUE(channel, title_key)
        )""")
        # Ambiguous sends remain locked long enough to prevent a duplicate,
        # then expire so a crashed process cannot block a channel forever.
        conn.execute("DELETE FROM publication_claims WHERE datetime(claimed_at) < datetime('now', '-24 hours')")
        conn.commit()


def claim_publication(channel: str, product_id: int, title: str) -> bool:
    init_atomic_publication_guard()
    key = _title_key(title)
    if not key or product_id is None:
        return False

    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO publication_claims(
                    channel,
                    product_id,
                    title_key,
                    claimed_at,
                    origin
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    channel,
                    int(product_id),
                    key,
                    datetime.now(timezone.utc).isoformat(),
                    PUBLICATION_ORIGIN,
                ),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def release_publication_claim(channel: str, product_id: int) -> None:
    init_atomic_publication_guard()
    with _connect() as conn:
        conn.execute("DELETE FROM publication_claims WHERE channel=? AND product_id=?", (channel, int(product_id)))
        conn.commit()


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def get_last_publication(product_id: int) -> Optional[sqlite3.Row]:
    """
    Devuelve la publicación más reciente del producto.
    """
    with _connect() as conn:
        return conn.execute(
            """
            SELECT *
            FROM publications
            WHERE product_id = ? AND origin = ?
            ORDER BY published_at DESC, id DESC
            LIMIT 1
            """,
            (product_id, PUBLICATION_ORIGIN),
        ).fetchone()


def get_today_publication_count() -> int:
    """
    Cuenta publicaciones del día natural actual en UTC.
    """
    today = datetime.now(timezone.utc).date().isoformat()

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM publications
            WHERE substr(published_at, 1, 10) = ?
              AND origin = ?
            """,
            (today, PUBLICATION_ORIGIN),
        ).fetchone()

    return int(row["total"])


def is_recent_duplicate(
    product_id: int,
    current_price: float,
    current_discount_pct: Optional[float],
    current_title: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Determina si la oferta debe bloquearse por publicación reciente.

    Devuelve:
        (bloqueada, motivo)
    """
    now = datetime.now(timezone.utc)

    # El mismo título no debe reaparecer durante la ventana de bloqueo,
    # incluso si procede de otro product_id. La excepción por mejora de
    # precio/descuento solo se aplica si el título ha cambiado.
    if current_title:
        current_key = title_key(current_title)
        if current_key:
            with _connect() as conn:
                recent = conn.execute(
                    """
                    SELECT title
                    FROM publications
                    WHERE published_at >= ? AND origin = ?
                    ORDER BY published_at DESC, id DESC
                    """,
                    ((now - timedelta(days=REPEAT_BLOCK_DAYS)).isoformat(), PUBLICATION_ORIGIN),
                ).fetchall()
            if any(title_key(row["title"]) == current_key for row in recent):
                return True, "titulo_duplicado_reciente"

    last = get_last_publication(product_id)

    if last is None:
        return False, "sin_publicacion_previa"

    last_dt = _parse_dt(last["published_at"])
    age = now - last_dt

    if age >= timedelta(days=REPEAT_BLOCK_DAYS):
        return False, f"ultima_publicacion_hace_{age.days}_dias"

    # Mejora relativa del precio. Si el título es distinto, una mejora
    # significativa puede justificar una nueva publicación.
    previous_price = float(last["price"])
    if previous_price > 0:
        price_improvement = (
            (previous_price - current_price)
            / previous_price
            * 100.0
        )
        if price_improvement >= REPEAT_PRICE_IMPROVEMENT_PCT:
            return False, f"precio_mejora_{price_improvement:.1f}pct"

    previous_discount = last["discount_pct"]
    if current_discount_pct is not None and previous_discount is not None:
        discount_improvement = (
            float(current_discount_pct) - float(previous_discount)
        )
        if discount_improvement >= REPEAT_DISCOUNT_IMPROVEMENT_POINTS:
            return False, f"descuento_mejora_{discount_improvement:.1f}_puntos"

    return (
        True,
        f"publicado_hace_{age.days}d_{age.seconds // 3600}h",
    )


def record_publication(
    product_id: int,
    source: str,
    external_id: str,
    title: str,
    category: Optional[str],
    price: float,
    discount_pct: Optional[float],
    score: Optional[float],
    telegram_message_id: Optional[int],
) -> int:
    """
    Registra una publicación después de que Telegram haya confirmado
    el envío correctamente.

    Devuelve el ID interno de la publicación.
    """
    published_at = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO publications (
                product_id,
                source,
                external_id,
                title,
                category,
                price,
                discount_pct,
                score,
                telegram_message_id,
                published_at,
                origin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                source,
                external_id,
                title,
                category,
                price,
                discount_pct,
                score,
                telegram_message_id,
                published_at,
                PUBLICATION_ORIGIN,
            ),
        )

        conn.commit()
        return int(cur.lastrowid)


def get_recent_category_counts(hours: int = 18) -> dict[str, int]:
    """Cuenta categorías publicadas recientemente para favorecer variedad."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=int(hours))
    ).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) AS total
            FROM publications
            WHERE published_at >= ?
              AND origin = ?
              AND category IS NOT NULL
              AND category != ''
            GROUP BY category
            """,
            (cutoff, PUBLICATION_ORIGIN),
        ).fetchall()
    return {str(row["category"]): int(row["total"]) for row in rows}


def get_today_category_count(category: str) -> int:
    """Cuenta publicaciones de una categoría desde el inicio del día UTC."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM publications WHERE category=? AND published_at >= ? AND origin = 'tech'",
            (category, today),
        ).fetchone()
    return int(row["total"] if row else 0)


def get_publication_stats() -> dict:
    """
    Estadísticas sencillas para las comprobaciones de seguridad.
    """
    with _connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS total FROM publications WHERE origin = 'tech'"
        ).fetchone()["total"]

        unique_products = conn.execute(
            """
            SELECT COUNT(DISTINCT product_id) AS total
            FROM publications
            WHERE origin = 'tech'
            """
        ).fetchone()["total"]

    return {
        "total_publications": int(total),
        "unique_products": int(unique_products),
        "today": get_today_publication_count(),
    }


def can_publish(
    run_publication_count: int,
    product_id: int,
    current_price: float,
    current_discount_pct: Optional[float],
    current_title: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Comprueba todas las condiciones de seguridad antes de publicar.

    Devuelve:
        (permitido, motivo)
    """

    # 1. Límite por ejecución
    if run_publication_count >= MAX_PUBLICATIONS_PER_RUN:
        return (
            False,
            f"limite_ejecucion_{MAX_PUBLICATIONS_PER_RUN}",
        )

    # 2. Límite diario
    today_count = get_today_publication_count()

    if today_count >= MAX_PUBLICATIONS_PER_DAY:
        return (
            False,
            f"limite_diario_{MAX_PUBLICATIONS_PER_DAY}",
        )

    # 3. Duplicado reciente
    duplicate, reason = is_recent_duplicate(
        product_id=product_id,
        current_price=current_price,
        current_discount_pct=current_discount_pct,
        current_title=current_title,
    )

    if duplicate:
        return False, reason

    return True, "publicacion_permitida"
