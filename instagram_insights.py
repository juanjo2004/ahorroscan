#!/usr/bin/env python3
"""Sincroniza Insights de publicaciones editoriales de Instagram."""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "instagram_content.db"
GRAPH = f"https://graph.instagram.com/{os.getenv('INSTAGRAM_API_VERSION', 'v26.0')}"
METRICS = ("views", "reach", "likes", "comments", "saved", "shares", "total_interactions")


def load_env() -> None:
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with db() as c:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(editorial_publications)")}
        additions = {
            "views": "INTEGER",
            "total_interactions": "INTEGER",
            "insights_updated_at": "TEXT",
            "insights_error": "TEXT",
        }
        for name, typ in additions.items():
            if name not in cols:
                c.execute(f"ALTER TABLE editorial_publications ADD COLUMN {name} {typ}")
        c.commit()


def api_insights(media_id: str) -> dict:
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    params = urllib.parse.urlencode({
        "metric": ",".join(METRICS),
        "access_token": token,
    })
    req = urllib.request.Request(
        f"{GRAPH}/{media_id}/insights?{params}",
        headers={"User-Agent": "AhorroScan/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def extract(payload: dict) -> dict:
    out = {}
    for item in payload.get("data", []):
        values = item.get("values") or []
        if values:
            value = values[-1].get("value")
            if isinstance(value, (int, float)):
                out[item["name"]] = int(value)
    return out


def main() -> int:
    load_env()
    init_db()
    if not os.getenv("INSTAGRAM_ACCESS_TOKEN"):
        raise RuntimeError("Falta INSTAGRAM_ACCESS_TOKEN")

    with db() as c:
        rows = c.execute(
            "SELECT id, media_id FROM editorial_publications "
            "WHERE status='PUBLISHED' AND media_id IS NOT NULL ORDER BY id"
        ).fetchall()

    ok = 0
    failed = 0
    for row in rows:
        now = datetime.now(timezone.utc).isoformat()
        try:
            stats = extract(api_insights(row["media_id"]))
            with db() as c:
                c.execute(
                    "UPDATE editorial_publications SET views=?, reach=?, likes=?, "
                    "comments=?, shares=?, saves=?, total_interactions=?, "
                    "insights_updated_at=?, insights_error=NULL WHERE id=?",
                    (
                        stats.get("views"),
                        stats.get("reach"),
                        stats.get("likes"),
                        stats.get("comments"),
                        stats.get("shares"),
                        stats.get("saved"),
                        stats.get("total_interactions"),
                        now,
                        row["id"],
                    ),
                )
                c.commit()
            ok += 1
            print(f"[INSTAGRAM-INSIGHTS] id={row['id']} media_id={row['media_id']} {stats}")
        except Exception as exc:
            with db() as c:
                c.execute(
                    "UPDATE editorial_publications SET insights_updated_at=?, "
                    "insights_error=? WHERE id=?",
                    (now, str(exc)[:1000], row["id"]),
                )
                c.commit()
            failed += 1
            print(
                f"[INSTAGRAM-INSIGHTS] FAILED id={row['id']} "
                f"media_id={row['media_id']}: {exc}"
            )

    print(f"[INSTAGRAM-INSIGHTS] synced={ok} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
