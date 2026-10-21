from __future__ import annotations

import os
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLICK_DB = BASE_DIR / "redirector" / "clicks.db"

PUBLIC_BASE_URL = os.getenv(
    "AHOROSCAN_REDIRECT_BASE_URL",
    "https://ahorroscan.es/go",
)


def _connect():
    CLICK_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CLICK_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links_v2 (
            code TEXT PRIMARY KEY,
            product_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clicks_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL,
            user_agent TEXT,
            source_ip TEXT,
            channel TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links_v3 (
            code TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            destination_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            channel TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_links_v3_product
        ON links_v3(project, product_id)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clicks_v3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            project TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL,
            user_agent TEXT,
            source_ip TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_clicks_v3_product_time
        ON clicks_v3(project, product_id, clicked_at)
    """)
    if "channel" not in {r[1] for r in conn.execute("PRAGMA table_info(links_v3)")}:
        conn.execute("ALTER TABLE links_v3 ADD COLUMN channel TEXT")
    if "channel" not in {r[1] for r in conn.execute("PRAGMA table_info(clicks_v3)")}:
        conn.execute("ALTER TABLE clicks_v3 ADD COLUMN channel TEXT")
    conn.commit()
    return conn


def _generate_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_or_create_product_link(
    product_id: int,
    destination_url: str | None = None,
    project: str = "tech",
    channel: str | None = None,
) -> str:
    """Devuelve un enlace público estable y trackeable por proyecto."""
    product_id = int(product_id)
    project = str(project).strip().lower() or "tech"
    channel = (str(channel).strip().lower() or None) if channel is not None else None

    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT code
            FROM links_v3
            WHERE project = ? AND product_id = ?
              AND COALESCE(channel, '') = COALESCE(?, '')
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (project, product_id, channel),
        ).fetchone()
        if row is not None:
            return f"{PUBLIC_BASE_URL}/{row['code']}"

        if project == "tech":
            legacy = conn.execute(
                """
                SELECT code
                FROM links_v2
                WHERE product_id = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (product_id,),
            ).fetchone()
            if legacy is not None:
                legacy_code = str(legacy["code"])
                if destination_url:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO links_v3 (
                            code, project, product_id,
                            destination_url, created_at, channel
                        )
                        VALUES (?, 'tech', ?, ?, ?, ?)
                        """,
                        (
                            legacy_code,
                            product_id,
                            str(destination_url),
                            datetime.now(timezone.utc).isoformat(),
                            channel,
                        ),
                    )
                    conn.commit()
                return f"{PUBLIC_BASE_URL}/{legacy_code}"

        if not destination_url:
            raise ValueError(
                "destination_url es obligatorio para crear un enlace nuevo"
            )

        while True:
            code = _generate_code()
            try:
                conn.execute(
                    """
                    INSERT INTO links_v3 (
                        code, project, product_id,
                        destination_url, created_at, channel
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        project,
                        product_id,
                        str(destination_url),
                        datetime.now(timezone.utc).isoformat(),
                        channel,
                    ),
                )
                conn.commit()
                return f"{PUBLIC_BASE_URL}/{code}"
            except sqlite3.IntegrityError:
                continue
    finally:
        conn.close()
