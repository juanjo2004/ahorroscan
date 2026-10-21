from __future__ import annotations

import html
import math
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from ha_publish_guard import deny_reason, publishing_enabled
import config as telegram_config
from telegram_api import TelegramOutcomeUnknown, TelegramRequestRejected, send as telegram_send
from selection import _tech_category_title_is_allowed
from product_relevance import is_repair_related

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "aggregator.db"
load_dotenv(ROOT / ".env")
TECH_DB = ROOT / "data" / "ofertas.db"
HOGAR_DB = Path(os.environ.get("AHOROSCAN_GLOBAL_DB", str(ROOT / "data" / "ofertas.db")))
CLICKS_DB = ROOT / "redirector" / "clicks.db"

CHAT_ID = os.getenv("AHOROSCAN_TELEGRAM_CHAT_ID", "-1004335220917")
MAX_PER_RUN = int(os.getenv("AHOROSCAN_MAX_PER_RUN", "6"))
MAX_PER_DAY = int(os.getenv("AHOROSCAN_MAX_PER_DAY", "12"))
LOOKBACK_DAYS = int(os.getenv("AHOROSCAN_AGGREGATOR_LOOKBACK_DAYS", "7"))
MIN_SCORE = float(os.getenv("AHOROSCAN_AGGREGATOR_MIN_SCORE", "60"))
PERFORMANCE_FILE = ROOT / "data" / "performance.json"
REAL_START_FILE = ROOT / "data" / "REAL_TRAFFIC_START.txt"

BLOCKED = {
    "funda", "fundas", "carcasa", "cable", "adaptador", "adaptadores",
    "soporte para", "repuesto", "repuestos", "recambio", "recambios",
    "keycaps", "reposamuñecas", "lámpara de trabajo", "lampara de trabajo",
    "linterna", "placa de desarrollo", "development board", "interruptor lineal",
}


def connect(path: Path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS aggregator_publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                product_id INTEGER,
                title TEXT NOT NULL,
                category TEXT,
                score REAL NOT NULL,
                telegram_message_id INTEGER,
                published_at TEXT NOT NULL,
                channel TEXT,
                UNIQUE(project, source, external_id)
            )
        """)
        columns = {row[1] for row in con.execute("PRAGMA table_info(aggregator_publications)")}
        if "channel" not in columns:
            con.execute("ALTER TABLE aggregator_publications ADD COLUMN channel TEXT")
        con.execute("CREATE INDEX IF NOT EXISTS idx_agg_pub_time ON aggregator_publications(published_at)")


def already_published(project, source, external_id):
    with connect(DB) as con:
        return con.execute(
            "SELECT 1 FROM aggregator_publications WHERE project=? AND source=? AND external_id=? LIMIT 1",
            (project, source, str(external_id)),
        ).fetchone() is not None


def today_count():
    today = datetime.now(timezone.utc).date().isoformat()
    with connect(DB) as con:
        return con.execute(
            "SELECT COUNT(*) FROM aggregator_publications WHERE substr(published_at,1,10)=?",
            (today,),
        ).fetchone()[0]


def click_counts():
    result = {}
    if not CLICKS_DB.exists():
        return result
    try:
        real_start = REAL_START_FILE.read_text().strip()
    except Exception:
        real_start = "9999-01-01T00:00:00+00:00"
    with connect(CLICKS_DB) as con:
        for r in con.execute("SELECT project,product_id,COUNT(*) clicks FROM clicks_v3 WHERE clicked_at>=? GROUP BY project,product_id",(real_start,)):
            result[(r["project"], int(r["product_id"]))] = int(r["clicks"])
    return result


def performance_feedback():
    """Devuelve una señal suavizada por categoría a partir de los últimos 30 días.
    Solo actúa cuando hay suficiente muestra, evitando que un solo clic cambie el ranking.
    """
    if not PERFORMANCE_FILE.exists(): return {}
    try: data=__import__("json").loads(PERFORMANCE_FILE.read_text())
    except Exception: return {}
    out={}
    for key,b in data.get("categories",{}).items():
        pubs=int(b.get("publications",0)); clicks=int(b.get("clicks",0))
        if pubs < 4: continue
        baseline=clicks/pubs
        # Referencia 0.5 clics/publicación. Acotado para no dominar la calidad intrínseca.
        delta=max(-3.0,min(3.0,(baseline-0.5)*2.0))
        out[key]=round(delta,3)
    return out
def _bad_title(title: str) -> bool:
    text = title.lower()
    return is_repair_related(text) or any(term in text for term in BLOCKED)


CATEGORY_TITLE_TERMS = {
    "laptops": ("portatil", "portátil", "laptop", "notebook", "macbook", "thinkpad", "ideapad", "vivobook", "aspire", "zenbook"),
    "projectors": ("proyector", "projector"),
    "monitors": ("monitor", "pantalla", "display"),
    "audio": ("auricular", "auriculares", "headphone", "headset", "altavoz", "speaker", "soundbar", "microfono", "micrófono"),
    "wearables": ("smartwatch", "reloj inteligente", "smart band", "pulsera inteligente", "fitness tracker"),
    "printers": ("impresora", "printer", "3d printer"),
    "cameras": ("camara", "cámara", "camera", "webcam", "action cam"),
}

CATEGORY_TITLE_BLOCKED = {
    "laptops": ("ratón", "raton", "mouse", "altavoz", "speaker", "bombilla", "lonchera", "disco duro externo"),
    "projectors": ("hud", "head up display", "pantalla de parabrisas"),
    "printers": ("hotend", "boquilla", "extrusora", "bloque de calor"),
}

def _category_title_ok(category, title):
    cat=(category or "").lower(); text=(title or "").lower()
    if any(term in text for term in CATEGORY_TITLE_BLOCKED.get(cat, ())): return False
    terms = CATEGORY_TITLE_TERMS.get(cat)
    return True if not terms else any(term in text for term in terms)


def _candidate_score(row, clicks, project, feedback=None):
    base = float(row["score"] or 0)
    discount = float(row["discount"] or 0)
    rating = float(row["rating"] or 0)
    reviews = int(row["reviews"] or 0)
    age_hours = max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(row["published_at"]).astimezone(timezone.utc)).total_seconds() / 3600)
    click_count = clicks.get((project, int(row["product_id"] or 0)), 0)

    score = base
    score += min(10.0, math.log1p(click_count) * 3.5)
    score += min(6.0, max(0.0, discount - 30.0) * 0.10)
    if rating >= 4.5:
        score += 3.0
    elif rating >= 4.2:
        score += 1.5
    if reviews >= 1000:
        score += 2.5
    elif reviews >= 200:
        score += 1.5
    score += max(-4.0, 2.0 - age_hours / 24.0)
    cat_key=f"{project}::{row.get('category') or 'otros'}"
    score += (feedback or {}).get(cat_key, 0.0)
    return round(score, 3), click_count


def load_candidates():
    """Carga publicaciones reales de todos los canales activos hacia el feed central.

    El canal general es una capa de curación: no vuelve a ejecutar los scanners
    verticales, sino que recoge lo que estos ya han publicado. Así evitamos que
    el agregador tenga una lógica de selección distinta de cada canal y, a la vez,
    damos a Instagram una única fuente central.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    rows = []

    # 1) Canales base: Tech y Hogar.
    with connect(TECH_DB) as con:
        q = """
        SELECT p.id publication_id, p.product_id, p.source, p.external_id, p.title,
               p.category, p.price, p.discount_pct discount, p.score, p.published_at,
               pr.image_url, pr.affiliate_url, pr.rating, pr.reviews
        FROM publications p LEFT JOIN products pr ON pr.id=p.product_id
        WHERE p.origin = 'tech' AND p.published_at >= ?
        """
        for r in con.execute(q, (cutoff,)):
            if r["product_id"] is None or _bad_title(r["title"]) or not _category_title_ok(r["category"], r["title"]):
                continue
            if not _tech_category_title_is_allowed(r["category"], r["title"]):
                continue
            rows.append({**dict(r), "project": "tech", "channel": "tech",
                         "merchant": "Amazon" if r["source"]=="amazon" else "AliExpress"})

    with connect(HOGAR_DB) as con:
        q = """
        SELECT p.id publication_id, p.product_id, p.source, p.external_id, p.title,
               pr.category, p.price, p.discount_percent discount, p.score, p.published_at,
               pr.image_url, p.affiliate_url, pr.rating, pr.reviews, p.merchant
        FROM publications p LEFT JOIN products pr ON pr.id=p.product_id
        WHERE p.origin = 'hogar' AND p.published_at >= ?
        """
        for r in con.execute(q, (cutoff,)):
            if r["product_id"] is None or _bad_title(r["title"]) or not _category_title_ok(r["category"], r["title"]):
                continue
            rows.append({**dict(r), "project": "hogar", "channel": "hogar",
                         "merchant": r["merchant"]})

    # 2) Canales verticales ya publicados. Todos comparten la DB global, pero
    # cada tabla representa una publicación efectiva en ese canal.
    vertical_tables = {
        "moviles": "mobile_publications",
        "mascotas": "pet_publications",
        "moda": "fashion_publications",
        "deportes": "sports_publications",
    }
    with connect(TECH_DB) as con:
        for channel, table in vertical_tables.items():
            rating_cols = "rating, reviews" if channel in {"moda", "deportes"} else "NULL AS rating, NULL AS reviews"
            q = f"""
            SELECT id publication_id, product_id, source, external_id, title,
                   category, price, discount_pct discount, score, published_at,
                   image_url, affiliate_url, {rating_cols}
            FROM {table}
            WHERE published_at >= ?
            """
            for r in con.execute(q, (cutoff,)):
                if r["product_id"] is None or _bad_title(r["title"]):
                    continue
                rows.append({**dict(r), "project": channel, "channel": channel,
                             "merchant": "Amazon" if r["source"]=="amazon" else "AliExpress"})

    return rows


def rank_candidates():
    init_db()
    clicks = click_counts()
    feedback = performance_feedback()
    ranked = []
    for row in load_candidates():
        if already_published("central", row["source"], row["external_id"]):
            continue
        s, c = _candidate_score(row, clicks, row["project"], feedback)
        if s < MIN_SCORE:
            continue
        row["global_score"] = s
        row["clicks"] = c
        ranked.append(row)
    ranked.sort(key=lambda x: x["global_score"], reverse=True)

    selected = []
    category_count = {}
    channel_count = {}

    # Primera pasada: asegurar presencia del mayor número posible de canales.
    # Solo entran candidatos que ya superaron MIN_SCORE, por lo que la diversidad
    # no se consigue rebajando la calidad.
    for row in ranked:
        channel = row.get("channel") or row["project"]
        cat = row["category"] or "otros"
        if channel_count.get(channel, 0) >= 1 or category_count.get(cat, 0) >= 1:
            continue
        selected.append(row)
        category_count[cat] = category_count.get(cat, 0) + 1
        channel_count[channel] = channel_count.get(channel, 0) + 1
        if len(selected) >= MAX_PER_RUN:
            return selected, ranked

    # Segunda pasada: completar el lote manteniendo variedad por categoría.
    for row in ranked:
        if row in selected:
            continue
        cat = row["category"] or "otros"
        if category_count.get(cat, 0) >= 2:
            continue
        selected.append(row)
        category_count[cat] = category_count.get(cat, 0) + 1
        channel = row.get("channel") or row["project"]
        channel_count[channel] = channel_count.get(channel, 0) + 1
        if len(selected) >= MAX_PER_RUN:
            break
    return selected, ranked
def tracking_url(product_id, destination_url):
    from redirector.link_manager import get_or_create_product_link
    return get_or_create_product_link(int(product_id), destination_url, "central", "telegram_central")


def keyboard(row):
    url = row["affiliate_url"]
    if not url:
        return None
    if row["source"] != "amazon":
        url = tracking_url(row["product_id"], url)
    return {"inline_keyboard": [[{"text": "🛒 VER OFERTA", "url": url}]]}


def message(row):
    title = html.escape(str(row["title"]).strip())
    price = float(row["price"])
    discount = row["discount"]
    channel_labels = {
        "tech": "AhorroScan Tech", "hogar": "AhorroScan Hogar",
        "moviles": "AhorroScan Móviles", "mascotas": "AhorroScan Mascotas",
        "moda": "AhorroScan Moda", "deportes": "AhorroScan Deportes",
    }
    project_label = channel_labels.get(row.get("channel") or row["project"], "AhorroScan")
    source_label = "Amazon" if row["source"] == "amazon" else "AliExpress"
    lines = [
        "⭐ <b>AHOROSCAN</b>",
        "",
        f"<b>{title}</b>",
        "",
        f"🔥 <b>Precio Oferta: {price:.2f} €</b>",
    ]
    if discount is not None and float(discount) > 0:
        lines.append(f"📉 <b>-{float(discount):.0f}%</b>")
    if row["rating"]:
        rating = float(row["rating"])
        reviews = int(row["reviews"] or 0)
        lines.append(f"⭐ {rating:.1f}/5" + (f" · {reviews:,} reseñas".replace(",", "." ) if reviews else ""))
    lines += [
        f"🏪 {html.escape(source_label)}",
        f"📌 Seleccionado desde {project_label}",
        "",
        "📣 <a href=\"https://ahorroscan.es\">Descubre todos los canales de AhorroScan</a>",
        "",
        "⚠️ Enlace de afiliado. Podemos recibir una comisión por compras elegibles, sin cambiar el precio.",
    ]
    return "\n".join(lines)


def telegram_request(token, method, payload):
    return telegram_send(token, method, payload, timeout=60)





def publish(selected):
    token = telegram_config.TELEGRAM_BOT_TOKEN.strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN no configurado")
    if today_count() >= MAX_PER_DAY:
        return [], "max_per_day"
    results = []
    sent = 0
    for row in selected:
        if sent >= MAX_PER_RUN or today_count() >= MAX_PER_DAY:
            break
        if not row["affiliate_url"]:
            continue
        payload = {
            "chat_id": CHAT_ID,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
            "text": message(row),
            "reply_markup": __import__("json").dumps(keyboard(row), ensure_ascii=False),
        }
        if row["image_url"]:
            payload["photo"] = row["image_url"]
            payload.pop("text")
            payload["caption"] = message(row)
            data = telegram_request(token, "sendPhoto", payload)
        else:
            data = telegram_request(token, "sendMessage", payload)
        mid = data["result"]["message_id"]
        now = datetime.now(timezone.utc).isoformat()
        with connect(DB) as con:
            con.execute("""INSERT OR IGNORE INTO aggregator_publications
                (project,source,external_id,product_id,title,category,score,telegram_message_id,published_at,channel)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                ("central", row["source"], str(row["external_id"]), row["product_id"], row["title"],
                 row["category"], row["global_score"], mid, now, row.get("channel") or row["project"]))
        sent += 1
        results.append((row, mid))
        time.sleep(1.2)
    return results, None


def main():
    selected, ranked = rank_candidates()
    print(f"[AGGREGATOR] candidatos_ranked={len(ranked)} seleccionados={len(selected)}")
    for r in selected:
        print(f"[AGGREGATOR] {r['global_score']:.2f} | {r['project']} | {r['source']} | {r['category']} | {r['price']:.2f}€ | {r['clicks']} clicks | {r['title'][:100]}")
    if os.getenv("AHOROSCAN_DRY_RUN", "0") == "1":
        return 0
    if not publishing_enabled("telegram"):
        print(f"[AGGREGATOR] BLOQUEADO HA: {deny_reason('telegram')}")
        return 0
    published, reason = publish(selected)
    print(f"[AGGREGATOR] PUBLICADAS={len(published)}" + (f" BLOQUEO={reason}" if reason else ""))
    for row, mid in published:
        print(f"[AGGREGATOR] OK message_id={mid} external_id={row['external_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
