import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from history import build_history_context
from brand_identity import extract_brand

DB_PATH = Path("data/ofertas.db")


def _ensure_columns(con, table, columns):
    existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, sql_type in columns.items():
        if name not in existing:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                affiliate_url TEXT,
                image_url TEXT,
                rating REAL,
                reviews INTEGER,
                category TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(source, external_id)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price REAL NOT NULL,
                captured_at TEXT,
                capture_date TEXT,
                origin TEXT NOT NULL DEFAULT 'tech',
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        _ensure_columns(con, "products", {
            "url": "TEXT", "affiliate_url": "TEXT", "image_url": "TEXT",
            "rating": "REAL", "reviews": "INTEGER", "category": "TEXT",
            "brand": "TEXT", "created_at": "TEXT", "updated_at": "TEXT",
        })
        _ensure_columns(con, "price_history", {
            "captured_at": "TEXT", "capture_date": "TEXT",
            "origin": "TEXT DEFAULT 'tech'",
        })
        con.execute("CREATE INDEX IF NOT EXISTS idx_price_history_product_date ON price_history(product_id, capture_date)")
        con.commit()


def upsert_product(offer):
    init_db()
    brand = getattr(offer, "brand", None) or extract_brand(offer.title)
    offer.brand = brand
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT id FROM products WHERE source=? AND external_id=?",
            (offer.source, offer.external_id),
        ).fetchone()
        if row:
            pid = int(row[0])
            con.execute("""
                UPDATE products
                SET title=?, url=?, affiliate_url=?, image_url=?, rating=?, reviews=?, category=?, brand=?, updated_at=?
                WHERE id=?
            """, (offer.title, offer.url, offer.affiliate_url, offer.image_url,
                  offer.rating, offer.reviews, offer.category, brand, now, pid))
        else:
            cur = con.execute("""
                INSERT INTO products
                (source, external_id, title, url, affiliate_url, image_url, rating, reviews, category, brand, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (offer.source, offer.external_id, offer.title, offer.url, offer.affiliate_url,
                  offer.image_url, offer.rating, offer.reviews, offer.category, brand, now, now))
            pid = int(cur.lastrowid)
        con.commit()
    return pid


def save_price_snapshot(product_id: int, price: float):
    init_db()
    now = datetime.now(timezone.utc)
    capture_date = now.date().isoformat()
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT id FROM price_history WHERE product_id=? AND capture_date=? AND origin='tech'",
            (product_id, capture_date),
        ).fetchone()
        if row:
            con.execute(
                "UPDATE price_history SET price=?, captured_at=? WHERE id=? AND origin='tech'",
                (float(price), now.isoformat(), row[0]),
            )
        else:
            con.execute(
                "INSERT INTO price_history(product_id, price, captured_at, capture_date, origin) VALUES (?, ?, ?, ?, 'tech')",
                (product_id, float(price), now.isoformat(), capture_date),
            )
        con.commit()


def get_prior_history(product_id: int, days: int = 30):
    init_db()
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days)
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("""
            SELECT price, capture_date
            FROM price_history
            WHERE product_id=?
              AND origin='tech'
              AND capture_date < ?
              AND capture_date >= ?
            ORDER BY capture_date ASC
        """, (product_id, today.isoformat(), cutoff.isoformat())).fetchall()


def get_history_stats(product_id: int, days: int = 30):
    return history_stats_from_rows(get_prior_history(product_id, days))


def history_stats_from_rows(rows):
    ctx = build_history_context(rows)
    return {
        "count": ctx.count,
        "average": ctx.average,
        "minimum": ctx.minimum,
        "maximum": ctx.maximum,
        "median": ctx.median,
        "reliable": ctx.reliable,
        "confidence": ctx.confidence,
    }
