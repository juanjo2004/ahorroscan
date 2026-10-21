#!/usr/bin/env python3
"""Informe de calibración. No modifica pesos automáticamente."""
import sqlite3
from statistics import mean, median
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "ofertas.db"
CLICK_DB = ROOT / "redirector" / "clicks.db"
MIN_PUBLICATIONS = 100
MIN_CLICKS = 30


def click_metrics():
    if not CLICK_DB.exists():
        return {"all_clicks": 0, "attributed_clicks": 0, "unattributed_clicks": 0}
    with sqlite3.connect(CLICK_DB) as con:
        tables = {
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        all_clicks = sum(
            con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("clicks", "clicks_v2") if table in tables
        )
        if "clicks_v2" not in tables:
            return {"all_clicks": all_clicks, "attributed_clicks": 0, "unattributed_clicks": all_clicks}
        con.execute(f"ATTACH DATABASE '{DB}' AS main_db")
        attributed = con.execute("""
            SELECT COUNT(*)
            FROM clicks_v2 c
            JOIN main_db.publications p
              ON p.product_id = c.product_id
             AND p.published_at <= c.clicked_at
            WHERE NOT EXISTS (
                SELECT 1 FROM main_db.publications p2
                WHERE p2.product_id = c.product_id
                  AND p2.published_at > p.published_at
                  AND p2.published_at <= c.clicked_at
            )
        """).fetchone()[0]
        return {
            "all_clicks": all_clicks,
            "attributed_clicks": int(attributed),
            "unattributed_clicks": max(0, all_clicks - int(attributed)),
        }


def main():
    with sqlite3.connect(DB) as con:
        scores = [
            float(row[0])
            for row in con.execute(
                "SELECT score FROM publications WHERE origin='tech' AND score IS NOT NULL"
            ).fetchall()
        ]
    clicks = click_metrics()
    print("=== CALIBRACIÓN TECH ===")
    print("Publicaciones con score:", len(scores))
    print("Clics totales registrados:", clicks["all_clicks"])
    print("Clics atribuidos a publicaciones:", clicks["attributed_clicks"])
    print("Clics sin atribución:", clicks["unattributed_clicks"])
    if scores:
        print("Score media:", round(mean(scores), 2))
        print("Score mediana:", round(median(scores), 2))

    enough = (
        len(scores) >= MIN_PUBLICATIONS
        and clicks["attributed_clicks"] >= MIN_CLICKS
    )
    print(
        "Muestra suficiente para recalibrar:",
        "SÍ" if enough else "NO",
    )
    if not enough:
        print(
            "No se cambian pesos automáticamente: faltan datos de "
            "comportamiento atribuido de forma consistente."
        )


if __name__ == "__main__":
    main()
