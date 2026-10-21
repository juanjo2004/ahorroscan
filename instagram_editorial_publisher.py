#!/usr/bin/env python3
"""Publicador independiente del contenido editorial de AhorroScan en Instagram."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from ha_publish_guard import deny_reason, publishing_enabled

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "instagram_content.db"
LOCK = ROOT / "data" / "instagram_editorial_publish.lock"
GRAPH = f"https://graph.instagram.com/{os.getenv('INSTAGRAM_API_VERSION', 'v26.0')}"
MAX_PER_DAY = int(os.getenv("INSTAGRAM_EDITORIAL_MAX_PER_DAY", "1"))


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
        for name, typ in (
            ("container_id", "TEXT"),
            ("attempts", "INTEGER NOT NULL DEFAULT 0"),
            ("error_message", "TEXT"),
        ):
            if name not in cols:
                c.execute(f"ALTER TABLE editorial_publications ADD COLUMN {name} {typ}")
        c.commit()


def api(method: str, path: str, params: dict) -> dict:
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    params = dict(params)
    params["access_token"] = token
    url = GRAPH + path
    if method == "GET":
        req = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params), method="GET"
        )
    else:
        req = urllib.request.Request(
            url, data=urllib.parse.urlencode(params).encode(), method=method
        )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Instagram API HTTP {e.code}: {e.read().decode(errors='replace')}"
        ) from e


def today_count() -> int:
    day = datetime.now(timezone.utc).date().isoformat()
    with db() as c:
        return c.execute(
            "SELECT COUNT(*) FROM editorial_publications "
            "WHERE status='PUBLISHED' AND substr(published_at,1,10)=?",
            (day,),
        ).fetchone()[0]


def choose_content():
    with db() as c:
        rows = c.execute(
            "SELECT * FROM editorial_publications WHERE status='GENERATED' "
            "ORDER BY generated_at DESC, id DESC"
        ).fetchall()
        if len(rows) > 1:
            for old in rows[1:]:
                c.execute(
                    "UPDATE editorial_publications SET status='SUPERSEDED', "
                    "error_message=? WHERE id=?",
                    ("Reemplazada por una pieza editorial más reciente.", old["id"]),
                )
            c.commit()
        return rows[0] if rows else None


def mark_publishing(content_id: int) -> None:
    with db() as c:
        c.execute(
            "UPDATE editorial_publications SET status='PUBLISHING', "
            "attempts=COALESCE(attempts,0)+1, error_message=NULL WHERE id=?",
            (content_id,),
        )
        c.commit()


def mark_failed(content_id: int, exc: Exception) -> None:
    msg = str(exc)[:1000]
    with db() as c:
        c.execute(
            "UPDATE editorial_publications SET status='FAILED', error_message=? "
            "WHERE id=?",
            (msg, content_id),
        )
        c.commit()


def wait_container(ig_object: str, container_id: str) -> None:
    for _ in range(20):
        st = api("GET", f"/{container_id}", {
            "fields": "id,status_code,status"
        })
        code = st.get("status_code")
        print(f"[INSTAGRAM-EDITORIAL] container={container_id} status={code}")
        if code == "FINISHED":
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Container no publicable: {st}")
        time.sleep(3)
    raise RuntimeError("Timeout esperando container editorial")

def publish(content) -> str:
    me = api("GET", "/me", {"fields": "id,user_id,username,name"})
    expected_user = os.getenv("INSTAGRAM_USER_ID")
    if expected_user and me.get("user_id") != expected_user:
        raise RuntimeError(
            f"Cuenta Instagram inesperada: user_id={me.get('user_id')}"
        )
    ig_object = me["id"]
    print(
        f"[INSTAGRAM-EDITORIAL] cuenta=@{me.get('username')} "
        f"user_id={me.get('user_id')}"
    )
    if not content["image_path"].startswith("/"):
        raise RuntimeError("image_path no es una ruta local absoluta")
    image_url = content["public_url"]
    req = urllib.request.Request(
        image_url, headers={"User-Agent": "AhorroScan/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Imagen editorial HTTP {response.status}")
        if not (response.headers.get("Content-Type") or "").startswith("image/"):
            raise RuntimeError("La URL editorial no devuelve una imagen")

    created = api("POST", f"/{ig_object}/media", {
        "image_url": image_url,
        "caption": content["caption"],
    })
    container_id = created["id"]
    with db() as c:
        c.execute(
            "UPDATE editorial_publications SET container_id=? WHERE id=?",
            (container_id, content["id"]),
        )
        c.commit()
    wait_container(ig_object, container_id)

    last_error = None
    media_id = None
    for attempt in range(6):
        try:
            pub = api("POST", f"/{ig_object}/media_publish", {
                "creation_id": container_id
            })
            media_id = pub["id"]
            break
        except RuntimeError as exc:
            last_error = exc
            if "Media ID is not available" not in str(exc) or attempt == 5:
                raise
            print(f"[INSTAGRAM-EDITORIAL] reintento media_publish {attempt + 1}/5")
            time.sleep(5)
    if not media_id:
        raise last_error or RuntimeError("Instagram no devolvió media_id")

    published_at = datetime.now(timezone.utc).isoformat()
    with db() as c:
        c.execute(
            "UPDATE editorial_publications SET status='PUBLISHED', media_id=?, "
            "published_at=?, error_message=NULL WHERE id=?",
            (media_id, published_at, content["id"]),
        )
        c.commit()
    return media_id

def main() -> int:
    load_env()
    init_db()
    if ARGS.publish and not publishing_enabled("instagram"):
        print(f"[INSTAGRAM-EDITORIAL] BLOQUEADA HA: {deny_reason('instagram')}")
        return 0
    if not os.getenv("INSTAGRAM_ACCESS_TOKEN"):
        raise RuntimeError("Falta INSTAGRAM_ACCESS_TOKEN")
    if today_count() >= MAX_PER_DAY:
        print("[INSTAGRAM-EDITORIAL] límite diario alcanzado")
        return 0

    content = choose_content()
    if not content:
        print("[INSTAGRAM-EDITORIAL] no hay piezas GENERATED pendientes")
        return 0

    print(
        f"[INSTAGRAM-EDITORIAL] id={content['id']} "
        f"type={content['content_type']} generado={content['generated_at']}"
    )
    print(f"[INSTAGRAM-EDITORIAL] public_url={content['public_url']}")
    if not ARGS.publish:
        print("[INSTAGRAM-EDITORIAL] DRY RUN: no se publica")
        return 0

    mark_publishing(content["id"])
    try:
        media_id = publish(content)
    except Exception as exc:
        mark_failed(content["id"], exc)
        print(f"[INSTAGRAM-EDITORIAL] FAILED: {exc}")
        return 1
    print(f"[INSTAGRAM-EDITORIAL] PUBLISHED media_id={media_id}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--publish", action="store_true",
        help="Publica realmente la pieza editorial pendiente"
    )
    ARGS = parser.parse_args()

    # Evita dos publicaciones simultáneas desde cron/manual.
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("[INSTAGRAM-EDITORIAL] ya hay otra ejecución en curso")
            raise SystemExit(0)
        raise SystemExit(main())
