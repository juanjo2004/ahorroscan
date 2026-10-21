#!/usr/bin/env python3
"""Resumen de salud y rendimiento de AhorroScan Tech, solo lectura."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "ofertas.db"
CLICK_DB = ROOT / "redirector" / "clicks.db"
SOURCE_HEALTH = ROOT / "data" / "source_health.json"


def db_counts():
    with sqlite3.connect(DB) as con:
        result = {}
        for table in ("products", "price_history", "publications"):
            if table == "products":
                result[table] = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            else:
                result[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        result["published_products"] = con.execute(
            "SELECT COUNT(DISTINCT product_id) FROM publications WHERE origin='tech'"
        ).fetchone()[0]
        return result


def click_counts():
    if not CLICK_DB.exists():
        return {"clicks": 0, "schema": "missing"}
    with sqlite3.connect(CLICK_DB) as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        total = 0
        for table in ("clicks", "clicks_v2"):
            if table in tables:
                total += con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return {"clicks": total, "schema": sorted(tables)}


def publication_buckets():
    with sqlite3.connect(DB) as con:
        return con.execute(
            """SELECT CASE
                WHEN score < 60 THEN '<60'
                WHEN score < 65 THEN '60-64.99'
                WHEN score < 70 THEN '65-69.99'
                WHEN score < 75 THEN '70-74.99'
                ELSE '75+'
            END AS bucket, COUNT(*)
            FROM publications
            WHERE origin='tech'
            GROUP BY bucket
            ORDER BY bucket"""
        ).fetchall()


def main():
    try:
        source_health = json.loads(
            SOURCE_HEALTH.read_text(encoding="utf-8")
        )
    except Exception:
        source_health = {}

    attributed = 0
    total_clicks = 0
    if CLICK_DB.exists():
        with sqlite3.connect(CLICK_DB) as click_con, sqlite3.connect(DB) as main_con:
            tables = {
                r[0] for r in click_con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table in ("clicks", "clicks_v2"):
                if table in tables:
                    total_clicks += click_con.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
            if "clicks_v2" in tables:
                for product_id, clicked_at in click_con.execute(
                    "SELECT product_id, clicked_at FROM clicks_v2"
                ):
                    if main_con.execute(
                        """
                        SELECT 1
                        FROM publications
                        WHERE origin='tech' AND product_id = ? AND published_at <= ?
                        ORDER BY published_at DESC
                        LIMIT 1
                        """,
                        (product_id, clicked_at),
                    ).fetchone():
                        attributed += 1

    editorial = {}
    editorial_db = ROOT / "data" / "instagram_content.db"
    if editorial_db.exists():
        with sqlite3.connect(editorial_db) as editorial_con:
            row = editorial_con.execute(
                """SELECT COUNT(*), COALESCE(SUM(views),0), COALESCE(SUM(reach),0),
                          COALESCE(SUM(likes),0), COALESCE(SUM(comments),0),
                          COALESCE(SUM(shares),0), COALESCE(SUM(saves),0),
                          COALESCE(SUM(total_interactions),0)
                   FROM editorial_publications WHERE status='PUBLISHED'"""
            ).fetchone()
            editorial = {
                "publications": row[0], "views": row[1], "reach": row[2],
                "likes": row[3], "comments": row[4], "shares": row[5],
                "saves": row[6], "total_interactions": row[7],
            }

    monetization = {}
    monetization_file = ROOT / "data" / "monetization.json"
    if monetization_file.exists():
        try:
            monetization = json.loads(monetization_file.read_text(encoding="utf-8"))
        except Exception:
            monetization = {}

    print(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "telegram-bot-v2",
        "database": db_counts(),
        "clicks": click_counts(),
        "publication_score_buckets": publication_buckets(),
        "source_health": source_health,
        "click_attribution": {
            "total_clicks": total_clicks,
            "attributed_clicks": attributed,
            "unattributed_clicks": max(0, total_clicks - attributed),
        },
        "instagram_editorial": editorial,
        "monetization": monetization,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
