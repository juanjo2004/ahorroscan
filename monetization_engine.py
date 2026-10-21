#!/usr/bin/env python3
"""Capa de monetización AhorroScan: tráfico real, publicaciones y ledger."""
from __future__ import annotations
import os

import csv
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = ROOT / "redirector" / "clicks.db"
LEDGER = ROOT / "data" / "monetization.db"
REPORT = ROOT / "data" / "monetization.json"
INBOX = ROOT / "data" / "affiliate_reports" / "inbox"
ARCHIVE = ROOT / "data" / "affiliate_reports" / "processed"
REAL_START = ROOT / "data" / "REAL_TRAFFIC_START.txt"
TECH_DB = ROOT / "data" / "ofertas.db"
HOGAR_DB = Path(os.environ.get('AHOROSCAN_GLOBAL_DB', str(ROOT / 'data' / 'ofertas.db')))


def con(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def real_start():
    try:
        return datetime.fromisoformat(
            REAL_START.read_text().strip()
        ).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _qualified(user_agent):
    ua = str(user_agent or "").lower()
    blocked = ("ahorroscan-test", "ahorroscan-smoke", "ahoroscan-test", "ahoroscan-smoke", "curl/", "python-requests/")
    return not any(token in ua for token in blocked)


def _channel(raw, project=None):
    value = str(raw or "").strip().lower()
    if value:
        return value
    p = str(project or "").strip().lower()
    return p if p not in {"tech", "hogar", ""} else "unknown"


def _normalize_project(raw):
    value = str(raw or "").strip().lower()
    if value.startswith("hogar:") or value in {
        "hogar", "instagram_hogar", "telegram_hogar", "web_hogar"
    }:
        return "hogar"
    if value.startswith("tech:") or value in {
        "tech", "instagram_tech", "telegram_tech", "web_tech"
    }:
        return "tech"
    if value.startswith("instagram_"):
        return "instagram"
    if value.startswith("telegram_"):
        return "telegram"
    if value.startswith("web_"):
        return "web"
    return value or "unknown"


def _num(value):
    text = str(value or "").strip().replace("€", "").replace("EUR", "").replace(" ", "")
    try:
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        return float(text or 0)
    except Exception:
        return 0.0


def init():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    with con(LEDGER) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network TEXT NOT NULL,
                merchant TEXT,
                transaction_id TEXT,
                order_date TEXT,
                amount REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                currency TEXT DEFAULT 'EUR',
                status TEXT,
                source_file TEXT,
                product_id INTEGER,
                project TEXT,
                season TEXT,
                channel TEXT,
                external_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(network, transaction_id)
            )
        """)
        existing = {r[1] for r in c.execute("PRAGMA table_info(commissions)")}
        for name, typ in [
            ("product_id", "INTEGER"),
            ("project", "TEXT"),
            ("season", "TEXT"),
            ("channel", "TEXT"),
            ("external_id", "TEXT"),
            ("clickref", "TEXT"),
            ("click_id", "INTEGER"),
            ("attribution_method", "TEXT"),
            ("attribution_confidence", "REAL"),
            ("attributed_at", "TEXT"),
        ]:
            if name not in existing:
                c.execute(f"ALTER TABLE commissions ADD COLUMN {name} {typ}")

        c.execute("""
            CREATE TABLE IF NOT EXISTS click_attribution (
                click_id INTEGER PRIMARY KEY,
                code TEXT NOT NULL,
                clicked_at TEXT NOT NULL,
                project TEXT NOT NULL,
                channel TEXT,
                product_id INTEGER,
                external_id TEXT,
                title TEXT,
                category TEXT,
                source TEXT,
                merchant TEXT,
                destination_url TEXT,
                publication_id INTEGER,
                user_agent TEXT,
                qualified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_attr_project_channel
            ON click_attribution(project, channel, clicked_at)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_attr_product
            ON click_attribution(project, product_id, clicked_at)
        """)
        c.commit()


def _parse_clickref(raw):
    """Parsea clickrefs AhorroScan sin confundirlos con un canal."""
    value=str(raw or "").strip()
    if not value:
        return {"raw": None, "project": None, "channel": None, "merchant": None, "external_id": None}
    parts=value.split(":")
    first=parts[0].strip().lower()
    project=_normalize_project(first)
    if first in {"hogar","tech"} and len(parts)>=3:
        return {"raw":value,"project":project,"channel":None,
                "merchant":parts[1].strip().lower() or None,
                "external_id":":".join(parts[2:]).strip() or None}
    if first in {"instagram_hogar","instagram_tech","telegram_hogar","telegram_tech",
                 "telegram_central","web_hogar","web_tech"} and len(parts)>=3:
        return {"raw":value,"project":project,"channel":first,
                "merchant":parts[1].strip().lower() or None,
                "external_id":":".join(parts[2:]).strip() or None}
    return {"raw":value,"project":project if project in {"hogar","tech"} else None,
            "channel":first if first in {"instagram","telegram","web"} else None,
            "merchant":None,"external_id":None}


def _resolve_product_id(project, external_id):
    if not external_id or project not in {"tech","hogar"}:
        return None
    paths=(TECH_DB,) if project=="tech" else (HOGAR_DB,)
    for db_path in paths:
        if not db_path.exists():
            continue
        try:
            with con(db_path) as c:
                hit=c.execute(
                    "SELECT id FROM products WHERE external_id=? LIMIT 1",
                    (str(external_id),),
                ).fetchone()
                if hit:
                    return int(hit["id"])
        except Exception:
            pass
    return None


def _merchant_key(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _parse_order_datetime(value):
    text=str(value or "").strip()
    if not text:
        return None
    try:
        dt=datetime.fromisoformat(text.replace("Z","+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d","%d/%m/%Y %H:%M:%S","%d/%m/%Y"):
            try:
                return datetime.strptime(text,fmt).replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _attribute_commission(row):
    ref=_parse_clickref(row.get("clickref") or row.get("project"))
    project=ref["project"] or _normalize_project(row.get("project"))
    product_id=row.get("product_id")
    if product_id is not None:
        try: product_id=int(product_id)
        except Exception: product_id=None
    external_id=ref["external_id"] or row.get("external_id")
    if product_id is None:
        product_id=_resolve_product_id(project,external_id)
    merchant=row.get("merchant") or ref["merchant"]
    channel=ref["channel"] or (
        row.get("channel") if row.get("channel") else
        (_channel(None,project) if project else "unknown")
    )
    return {
        "project":project,
        "product_id":product_id,
        "external_id":external_id,
        "merchant":merchant,
        "channel":channel,
        "clickref":ref["raw"],
    }


def import_csvs():
    imported = 0
    for f in sorted(INBOX.glob("*")):
        if f.suffix.lower() not in {".csv", ".tsv", ".txt"}:
            continue
        try:
            with f.open(newline="", encoding="utf-8-sig") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                delim = "\t" if "\t" in sample else ("," if "," in sample else ";")
                rows = csv.DictReader(handle, delimiter=delim)
                for row in rows:
                    norm = {
                        str(k).strip().lower(): v
                        for k, v in row.items()
                        if k is not None
                    }

                    def pick(*names):
                        for name in names:
                            if name.lower() in norm:
                                return norm[name.lower()]
                        return ""

                    network = pick("network", "red", "source") or (
                        "amazon" if "amazon" in f.name.lower()
                        else f.stem.split("_")[0]
                    )
                    tx = pick(
                        "transaction_id", "transaction id", "id",
                        "order_id", "order id", "order reference"
                    )
                    if not tx:
                        continue

                    pid = pick("product_id", "product id", "sku_product_id")
                    try:
                        pid = int(pid) if pid else None
                    except Exception:
                        pid = None

                    clickref = pick(
                        "clickref", "click_ref", "click ref",
                        "tracking id", "tracking_id"
                    ) or None
                    raw_project = pick(
                        "project", "campaign_project"
                    ) or None
                    raw_channel = pick("channel", "source_channel") or None
                    merchant = pick("merchant", "advertiser", "program")
                    attr = _attribute_commission({
                        "project": raw_project,
                        "channel": raw_channel,
                        "clickref": clickref,
                        "product_id": pid,
                        "external_id": pick("external_id", "external id"),
                        "merchant": merchant,
                    })
                    pid=attr["product_id"]
                    project=attr["project"]
                    merchant=merchant or attr["merchant"]
                    channel=raw_channel or attr["channel"]

                    with con(LEDGER) as c:
                        c.execute("""
                            INSERT OR IGNORE INTO commissions
                            (network, merchant, transaction_id, order_date,
                             amount, commission, currency, status, source_file,
                             product_id, project, season, channel, external_id,
                             clickref)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            network,
                            merchant or ("Amazon.es" if network == "amazon" else ""),
                            tx,
                            pick("order_date", "date", "transaction date", "order date/time"),
                            _num(pick("amount", "order_value", "sale_amount", "revenue")),
                            _num(pick(
                                "commission", "commission_amount",
                                "publisher_commission", "earnings",
                                "referral commission earnings"
                            )),
                            pick("currency") or "EUR",
                            pick("status", "transaction_status", "order status") or "reported",
                            f.name,
                            pid,
                            project,
                            pick("season", "seasonal_campaign", "campaign") or None,
                            channel,
                            attr["external_id"],
                            attr["clickref"],
                        ))
                        c.commit()
                    imported += 1
            f.rename(ARCHIVE / f.name)
        except Exception as exc:
            print(f"[MONETIZATION] ERROR {f.name}: {exc}")
    return imported


def _product_meta(project, product_id):
    if product_id is None:
        return {}

    path = TECH_DB if project == "tech" else HOGAR_DB if project == "hogar" else None
    if not path or not path.exists():
        return {}

    try:
        with con(path) as c:
            if project == "tech":
                row = c.execute("""
                    SELECT id, source, external_id, title, category, affiliate_url
                    FROM products WHERE id=? LIMIT 1
                """, (product_id,)).fetchone()
                if not row:
                    return {}
                data = dict(row)
                data["merchant"] = (
                    "Amazon" if data.get("source") == "amazon"
                    else "AliExpress" if data.get("source") == "aliexpress"
                    else data.get("source")
                )
                return data

            row = c.execute("""
                SELECT id, source, external_id, merchant, title, category, affiliate_url
                FROM products WHERE id=? LIMIT 1
            """, (product_id,)).fetchone()
            return dict(row) if row else {}
    except Exception:
        return {}


def _publication_id(project, product_id, clicked_at):
    if product_id is None:
        return None
    path = TECH_DB if project == "tech" else HOGAR_DB if project == "hogar" else None
    if not path or not path.exists():
        return None
    try:
        with con(path) as c:
            row = c.execute("""
                SELECT id FROM publications
                WHERE product_id=? AND published_at<=?
                  AND origin=?
                ORDER BY published_at DESC LIMIT 1
            """, (product_id, clicked_at, project)).fetchone()
            return int(row["id"]) if row else None
    except Exception:
        return None


def sync_click_ledger():
    init()
    with con(DB) as src, con(LEDGER) as dst:
        click_cols = {r[1] for r in src.execute("PRAGMA table_info(clicks_v3)")}
        link_cols = {r[1] for r in src.execute("PRAGMA table_info(links_v3)")}
        click_channel = ", c.channel AS click_channel" if "channel" in click_cols else ""
        link_channel = ", l.channel AS link_channel" if "channel" in link_cols else ""

        rows = src.execute(f"""
            SELECT c.id, c.code, c.project, c.product_id, c.clicked_at,
                   c.user_agent, l.destination_url
                   {click_channel} {link_channel}
            FROM clicks_v3 c
            LEFT JOIN links_v3 l ON l.code=c.code
            WHERE c.clicked_at>=?
            ORDER BY c.id
        """, (real_start().isoformat(),)).fetchall()

        for row in rows:
            data = dict(row)
            project = _normalize_project(data.get("project"))
            channel = (
                data.get("click_channel")
                or data.get("link_channel")
                or _channel(None, project)
            )
            meta = _product_meta(project, data.get("product_id"))
            merchant = (
                meta.get("merchant")
                or meta.get("source")
                or (urlparse(data.get("destination_url") or "").netloc or None)
            )
            dst.execute("""
                INSERT OR REPLACE INTO click_attribution
                (click_id, code, clicked_at, project, channel, product_id,
                 external_id, title, category, source, merchant,
                 destination_url, publication_id, user_agent, qualified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"],
                data["code"],
                data["clicked_at"],
                project,
                channel,
                data.get("product_id"),
                meta.get("external_id"),
                meta.get("title"),
                meta.get("category"),
                meta.get("source"),
                merchant,
                data.get("destination_url"),
                _publication_id(
                    project,
                    data.get("product_id"),
                    data["clicked_at"],
                ),
                data.get("user_agent"),
                int(_qualified(data.get("user_agent"))),
            ))
        dst.commit()
        return len(rows)


def attribute_commissions():
    """Relaciona ventas con el último clic compatible antes de la venta."""
    init()
    now=datetime.now(timezone.utc).isoformat()
    matched=0
    with con(LEDGER) as c:
        rows=c.execute("""
            SELECT id, network, merchant, order_date, product_id, project,
                   channel, external_id, clickref
            FROM commissions
            WHERE click_id IS NULL
        """).fetchall()
        for row in rows:
            ref=_parse_clickref(row["clickref"])
            project=row["project"] or ref["project"]
            channel=row["channel"] or ref["channel"]
            merchant=_merchant_key(row["merchant"] or ref["merchant"])
            external_id=row["external_id"] or ref["external_id"]
            product_id=row["product_id"] or _resolve_product_id(project,external_id)
            order_dt=_parse_order_datetime(row["order_date"])
            if not order_dt:
                continue

            # 1) Si el clickref coincide exactamente con un código del redirector.
            click=None
            exact_clickref=False
            if row["clickref"]:
                click=c.execute("""
                    SELECT click_id, code, project, channel, product_id, merchant
                    FROM click_attribution
                    WHERE code=? AND qualified=1
                    ORDER BY clicked_at DESC LIMIT 1
                """,(row["clickref"],)).fetchone()
                exact_clickref=bool(click)

            # 2) Coincidencia por producto/external_id/merchant, último clic anterior.
            if not click and product_id is not None:
                params=[project,product_id,order_dt.isoformat()]
                sql="""
                    SELECT click_id, project, channel, product_id, merchant
                    FROM click_attribution
                    WHERE qualified=1 AND project=? AND product_id=?
                      AND clicked_at<=?
                """
                if merchant:
                    sql+=" AND lower(replace(replace(COALESCE(merchant,''),'-',''),' ','')) LIKE ?"
                    params.append("%"+merchant+"%")
                sql+=" ORDER BY clicked_at DESC LIMIT 1"
                click=c.execute(sql,params).fetchone()

            if not click and external_id and project:
                click=c.execute("""
                    SELECT click_id, project, channel, product_id, merchant
                    FROM click_attribution
                    WHERE qualified=1 AND project=? AND external_id=?
                      AND clicked_at<=?
                    ORDER BY clicked_at DESC LIMIT 1
                """,(project,external_id,order_dt.isoformat())).fetchone()

            if click:
                method="exact_clickref" if exact_clickref else (
                    "product_nearest_click" if product_id is not None else "external_id_nearest_click"
                )
                confidence=1.0 if method=="exact_clickref" else 0.85
                c.execute("""
                    UPDATE commissions
                    SET product_id=COALESCE(product_id,?),
                        project=COALESCE(project,?),
                        channel=COALESCE(channel,?),
                        click_id=?,
                        attribution_method=?,
                        attribution_confidence=?,
                        attributed_at=?
                    WHERE id=?
                """,(click["product_id"],click["project"],click["channel"],
                     click["click_id"],method,confidence,now,row["id"]))
                matched+=1
            else:
                c.execute("""
                    UPDATE commissions
                    SET product_id=COALESCE(product_id,?),
                        project=COALESCE(project,?),
                        channel=COALESCE(channel,?),
                        attribution_method=COALESCE(attribution_method,'unassigned'),
                        attribution_confidence=COALESCE(attribution_confidence,0)
                    WHERE id=?
                """,(product_id,project,channel,row["id"]))
        c.commit()
    return matched


def build():
    init()
    synced = sync_click_ledger()
    attributed = attribute_commissions()
    cutoff = max(
        datetime.now(timezone.utc) - timedelta(days=30),
        real_start(),
    ).isoformat()

    with con(LEDGER) as c:
        ledger = c.execute("""
            SELECT project, channel, merchant, product_id, external_id,
                   title, category, COUNT(*) clicks,
                   MIN(clicked_at) first_click, MAX(clicked_at) last_click
            FROM click_attribution
            WHERE clicked_at>=? AND qualified=1
            GROUP BY project, channel, merchant, product_id, external_id,
                     title, category
            ORDER BY clicks DESC, last_click DESC
            LIMIT 100
        """, (cutoff,)).fetchall()

        by_project = [
            dict(r) for r in c.execute("""
                SELECT project, COUNT(*) clicks
                FROM click_attribution
                WHERE clicked_at>=? AND qualified=1
                GROUP BY project ORDER BY clicks DESC
            """, (cutoff,))
        ]
        by_channel = [
            dict(r) for r in c.execute("""
                SELECT channel, COUNT(*) clicks
                FROM click_attribution
                WHERE clicked_at>=? AND qualified=1
                GROUP BY channel ORDER BY clicks DESC
            """, (cutoff,))
        ]
        by_merchant = [
            dict(r) for r in c.execute("""
                SELECT merchant, COUNT(*) clicks
                FROM click_attribution
                WHERE clicked_at>=? AND qualified=1
                GROUP BY merchant ORDER BY clicks DESC
            """, (cutoff,))
        ]
        by_category = [
            dict(r) for r in c.execute("""
                SELECT project, category, COUNT(*) clicks
                FROM click_attribution
                WHERE clicked_at>=? AND qualified=1
                GROUP BY project, category ORDER BY clicks DESC
            """, (cutoff,))
        ]
        coverage = c.execute("""
            SELECT COUNT(*) total,
                   SUM(CASE WHEN qualified=1 THEN 1 ELSE 0 END) qualified,
                   SUM(CASE WHEN qualified=1 AND product_id IS NOT NULL
                            THEN 1 ELSE 0 END) with_product,
                   SUM(CASE WHEN qualified=1
                              AND channel NOT IN ('', 'unknown')
                            THEN 1 ELSE 0 END) with_channel,
                   SUM(CASE WHEN qualified=1
                              AND merchant IS NOT NULL AND merchant<>''
                            THEN 1 ELSE 0 END) with_merchant
            FROM click_attribution
            WHERE clicked_at>=?
        """, (cutoff,)).fetchone()

        rev = [
            dict(r) for r in c.execute("""
                SELECT network, merchant, COUNT(*) transactions,
                       COALESCE(SUM(amount),0) sales,
                       COALESCE(SUM(commission),0) commission
                FROM commissions
                WHERE order_date>=date('now','-30 day')
                GROUP BY network, merchant
            """)
        ]
        totals = c.execute("""
            SELECT COUNT(*) n, COALESCE(SUM(commission),0) commission
            FROM commissions
        """).fetchone()
        totals30 = c.execute("""
            SELECT COUNT(*) n, COALESCE(SUM(commission),0) commission
            FROM commissions
            WHERE order_date>=date('now','-30 day')
        """).fetchone()
        revenue_project = [
            dict(r) for r in c.execute("""
                SELECT project, COUNT(*) transactions,
                       COALESCE(SUM(amount),0) sales,
                       COALESCE(SUM(commission),0) commission
                FROM commissions
                WHERE order_date>=date('now','-30 day')
                GROUP BY project ORDER BY commission DESC
            """)
        ]
        revenue_channel = [
            dict(r) for r in c.execute("""
                SELECT COALESCE(channel,'unknown') channel, COUNT(*) transactions,
                       COALESCE(SUM(amount),0) sales,
                       COALESCE(SUM(commission),0) commission
                FROM commissions
                WHERE order_date>=date('now','-30 day')
                GROUP BY COALESCE(channel,'unknown') ORDER BY commission DESC
            """)
        ]
        revenue_product_channel = [
            dict(r) for r in c.execute("""
                SELECT project, COALESCE(channel,'unknown') channel,
                       merchant, product_id, external_id,
                       COUNT(*) transactions,
                       COALESCE(SUM(amount),0) sales,
                       COALESCE(SUM(commission),0) commission,
                       COALESCE(SUM(CASE WHEN click_id IS NOT NULL THEN 1 ELSE 0 END),0) matched_transactions
                FROM commissions
                WHERE order_date>=date('now','-30 day')
                GROUP BY project, COALESCE(channel,'unknown'), merchant,
                         product_id, external_id
                ORDER BY commission DESC, sales DESC
            """)
        ]
        attribution_stats = [
            dict(r) for r in c.execute("""
                SELECT COALESCE(attribution_method,'unassigned') method,
                       COUNT(*) transactions,
                       COALESCE(SUM(commission),0) commission
                FROM commissions
                WHERE order_date>=date('now','-30 day')
                GROUP BY COALESCE(attribution_method,'unassigned')
            """)
        ]

    ledger_rows = [dict(r) for r in ledger]
    qualified_clicks = int(coverage["qualified"] or 0)
    transaction_count = int(totals30["n"])
    commission_total = float(totals30["commission"])

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": 30,
        "real_traffic_since": real_start().isoformat(),
        "clicks_by_project": by_project,
        "clicks_by_channel": by_channel,
        "clicks_by_merchant": by_merchant,
        "clicks_by_category": by_category,
        "top_clicked_products": ledger_rows[:20],
        "product_channel_ledger": ledger_rows,
        "ledger_coverage": dict(coverage),
        "ledger_synced_rows": synced,
        "qualified_click_definition": (
            "Excludes AhorroScan-Test/Smoke, curl and python-requests user agents"
        ),
        "revenue_by_network": rev,
        "revenue_by_project": revenue_project,
        "revenue_by_channel": revenue_channel,
        "revenue_by_product_channel": revenue_product_channel,
        "commission_attribution": attribution_stats,
        "attributed_transactions": attributed,
        "commission_total": commission_total,
        "transaction_count": transaction_count,
        "lifetime_commission_total": float(totals["commission"]),
        "lifetime_transaction_count": int(totals["n"]),
        "conversion_proxy": (
            round(transaction_count / qualified_clicks, 4)
            if qualified_clicks else 0.0
        ),
        "commission_per_click": (
            round(commission_total / qualified_clicks, 4)
            if qualified_clicks else 0.0
        ),
    }

    REPORT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"[MONETIZATION] ledger_rows_synced={synced} attributed_transactions={attributed} "
        f"qualified_clicks30d={qualified_clicks} "
        f"transactions={transaction_count} "
        f"commission={commission_total:.2f}€"
    )
    print(
        f"[MONETIZATION] channels={len(by_channel)} "
        f"merchants={len(by_merchant)} products={len(ledger_rows)}"
    )


if __name__ == "__main__":
    init()
    imported = import_csvs()
    print(f"[MONETIZATION] imported_rows={imported}")
    build()

