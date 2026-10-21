#!/usr/bin/env python3
"""Generador de resumen semanal AhorroScan. Solo genera borradores; no publica.

Fuentes: publicaciones efectivas de los canales durante la semana anterior.
Destino futuro: canal general de Telegram e Instagram, mediante integraciones separadas.
"""
from __future__ import annotations
import argparse, html, json, os, sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TECH_DB = Path(os.getenv('AHOROSCAN_WEEKLY_TECH_DB', str(ROOT / 'data' / 'ofertas.db')))
HOGAR_DB = Path(os.getenv('AHOROSCAN_WEEKLY_HOGAR_DB', str(ROOT / 'data' / 'ofertas.db')))
OUT_DIR = Path(os.getenv('AHOROSCAN_WEEKLY_OUT', str(ROOT / 'data' / 'weekly-summary')))
TZ = ZoneInfo('Europe/Madrid')
CHANNEL_TABLES = {
    'tech': ('publications', 'origin = ?', ('tech',)),
    'hogar': ('publications', 'origin = ?', ('hogar',)),
    'moviles': ('mobile_publications', '1=1', ()),
    'mascotas': ('pet_publications', '1=1', ()),
    'moda': ('fashion_publications', '1=1', ()),
    'deportes': ('sports_publications', '1=1', ()),
}
LABELS = {'tech':'💻 TECH','hogar':'🏠 HOGAR','moviles':'📱 MÓVILES','mascotas':'🐾 MASCOTAS','moda':'👕 MODA','deportes':'🏃 DEPORTES'}


def week_window(now=None):
    """Previous Monday 00:00 through Sunday 00:00, in Europe/Madrid."""
    local = (now or datetime.now(TZ)).astimezone(TZ)
    this_monday = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    start = this_monday - timedelta(days=7)
    end = this_monday
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat(), start, end


def _db(path):
    c = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    return c


def load_weekly_publications(start_utc, end_utc, tech_db=TECH_DB, hogar_db=HOGAR_DB):
    """Load real posted rows, merging shared vertical tables and removing duplicates."""
    found = []
    configs = [('tech', tech_db), ('moviles', tech_db), ('mascotas', tech_db),
               ('moda', tech_db), ('deportes', tech_db), ('hogar', hogar_db)]
    for channel, path in configs:
        if not path.exists():
            continue
        table, where, extra = CHANNEL_TABLES[channel]
        with _db(path) as con:
            tables = {r['name'] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if table not in tables:
                continue
            cols = {r['name'] for r in con.execute(f'PRAGMA table_info({table})')}
            required = {'product_id','title','published_at','price','source','external_id'}
            if not required.issubset(cols):
                continue
            # Some vertical tables hold their own affiliate/image snapshots; ordinary publications use products.
            if table == 'publications':
                sql = f'''SELECT p.product_id,p.source,p.external_id,p.title,p.category,p.price,
                    p.discount_pct AS discount,p.score,p.published_at,p.affiliate_url AS published_affiliate,
                    pr.affiliate_url,pr.image_url,pr.current_price,pr.original_price,pr.availability,
                    pr.rating,pr.reviews,pr.updated_at
                    FROM publications p LEFT JOIN products pr ON pr.id=p.product_id
                    WHERE p.published_at >= ? AND p.published_at < ? AND {where}'''
            else:
                sql = f'''SELECT v.product_id,v.source,v.external_id,v.title,v.category,v.price,
                    v.discount_pct AS discount,v.score,v.published_at,
                    v.affiliate_url AS published_affiliate,v.image_url,
                    pr.affiliate_url,pr.current_price,pr.original_price,pr.availability,
                    pr.rating,pr.reviews,pr.updated_at
                    FROM {table} v LEFT JOIN products pr ON pr.id=v.product_id
                    WHERE v.published_at >= ? AND v.published_at < ?'''
            for row in con.execute(sql, (start_utc, end_utc, *extra)):
                d = dict(row)
                d['channel'] = channel
                d['affiliate_url'] = d.get('published_affiliate') or d.get('affiliate_url')
                # The historic publication proves it was posted; current availability is only trusted
                # when the product record explicitly says available and its price is populated.
                avail = str(d.get('availability') or '').strip().lower()
                # Only trust fresh, matching catalog prices. Unknown stock is not a positive confirmation.
                updated = str(d.get('updated_at') or '').strip()
                fresh = False
                if updated:
                    try:
                        stamp = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
                        fresh = (datetime.now(timezone.utc) - stamp).total_seconds() <= 30 * 86400
                    except ValueError:
                        pass
                d['current_price_verified'] = False
                d['display_price'] = None
                if avail in {'out of stock','out_of_stock','unavailable','agotado','no disponible'}:
                    d['eligibility_reason'] = 'explicitly_out_of_stock'
                elif d.get('current_price') is not None and fresh:
                    try:
                        current, posted = float(d['current_price']), float(d['price'])
                        stock_ok = avail in {'in_stock','in stock','available','instock','disponible','true','1'}
                        unknown_stock = not avail
                        tolerance = 0.05 if stock_ok else 0.02
                        if current > 0 and posted > 0 and abs(current-posted)/posted <= tolerance and (stock_ok or unknown_stock):
                            d['current_price_verified'] = True
                            d['display_price'] = current
                            d['eligibility_reason'] = 'fresh_price_stock_confirmed' if stock_ok else 'fresh_matching_price_stock_unknown'
                        else:
                            d['eligibility_reason'] = 'price_changed_or_stock_unconfirmed'
                    except (TypeError, ValueError):
                        d['eligibility_reason'] = 'invalid_price'
                else:
                    d['eligibility_reason'] = 'no_fresh_current_price'
                if not d['affiliate_url'] or not d.get('title') or not d.get('price'):
                    continue
                found.append(d)
    # One product can be posted to several verticals. Keep one canonical copy, prioritizing its most specific channel.
    priority = {'moviles':0,'mascotas':0,'moda':0,'deportes':0,'hogar':1,'tech':2}
    unique = {}
    for row in found:
        key = (str(row.get('source') or '').lower(), str(row.get('external_id') or row.get('product_id')))
        old = unique.get(key)
        if old is None or priority.get(row['channel'],9) < priority.get(old['channel'],9):
            unique[key] = row
    return list(unique.values())


def choose_highlights(rows, per_channel=3, max_total=18):
    """Pick a balanced shortlist across the active verticals, deduplicated by product."""
    buckets = defaultdict(list)
    for row in rows:
        # Avoid asserting the deal is still live unless the catalog confirms stock and current price.
        if not row.get('current_price_verified'):
            continue
        try:
            current = float(row['current_price'])
            posted = float(row['price'])
        except (TypeError, ValueError):
            continue
        if current <= 0 or posted <= 0:
            continue
        # Exclude deals whose catalog price has moved more than 5% since publication.
        if abs(current - posted) / posted > 0.05:
            continue
        row['display_price'] = current
        row['rank_score'] = float(row.get('score') or 0) + min(20, max(0, float(row.get('discount') or 0)) * .15)
        buckets[row['channel']].append(row)
    selected = []
    for channel in ('tech','moviles','hogar','mascotas','moda','deportes'):
        ranked = sorted(buckets[channel], key=lambda r: (r['rank_score'], r.get('published_at') or ''), reverse=True)
        selected.extend(ranked[:per_channel])
    selected.sort(key=lambda r: (r['rank_score'], r.get('published_at') or ''), reverse=True)
    return selected[:max_total]


def eur(value):
    return f"{float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + ' €'


def render_telegram(rows, start_local, end_local):
    lines = ['🔥 <b>RESUMEN SEMANAL AhorroScan</b> 💥', '',
        f'✨ Las ofertas más destacadas que publicamos del {start_local:%d/%m} al {(end_local - timedelta(days=1)):%d/%m}.',
        'Incluimos solo productos con precio actual y disponibilidad confirmados.', '']
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['channel']].append(r)
    for channel in ('tech','moviles','hogar','mascotas','moda','deportes'):
        if not grouped[channel]:
            continue
        lines.append(f"<b>{LABELS[channel]}</b>")
        for r in grouped[channel]:
            title = html.escape(' '.join(str(r['title']).split())[:130])
            url = html.escape(str(r['affiliate_url']), quote=True)
            lines.append(f"👍 <a href=\"{url}\">{title}</a> · <b>{eur(r['display_price'])}</b>")
        lines.append('')
    lines += ['🔎 Más ofertas y canales: <a href="https://ahorroscan.es">ahorroscan.es</a>', '',
        '⚠️ Enlaces de afiliado cuando corresponda. Los precios pueden cambiar.']
    return '\n'.join(lines)


def render_instagram(rows, start_local, end_local):
    lines = [f'🔥 RESUMEN SEMANAL AhorroScan 💥', '',
        f'Las ofertas más destacadas de la semana del {start_local:%d/%m} al {(end_local - timedelta(days=1)):%d/%m}.', '']
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['channel']].append(r)
    for channel in ('tech','moviles','hogar','mascotas','moda','deportes'):
        if not grouped[channel]: continue
        lines.append(LABELS[channel])
        for r in grouped[channel]:
            lines.append(f"• {r['title'][:90]}: {eur(r['display_price'])}")
        lines.append('')
    lines += ['🔗 Enlaces a las ofertas en ahorroscan.es', '',
        'Los precios y la disponibilidad pueden cambiar. Enlaces de afiliado cuando corresponda.',
        '#AhorroScan #ResumenSemanal #Ofertas #Chollos #Ahorro']
    return '\n'.join(lines)[:2150]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true', help='Generate previews only; default mode is also dry-run')
    ap.add_argument('--per-channel', type=int, default=3)
    ap.add_argument('--max-total', type=int, default=18)
    args = ap.parse_args()
    start_utc, end_utc, start_local, end_local = week_window()
    rows = load_weekly_publications(start_utc, end_utc)
    selected = choose_highlights(rows, args.per_channel, args.max_total)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {'generated_at': datetime.now(timezone.utc).isoformat(), 'period_start': start_local.isoformat(),
        'period_end_exclusive': end_local.isoformat(), 'source_rows': len(rows), 'selected_count': len(selected),
        'telegram_html': render_telegram(selected, start_local, end_local),
        'instagram_caption': render_instagram(selected, start_local, end_local),
        'offers': [{k:r.get(k) for k in ('channel','source','external_id','product_id','title','price','display_price','discount','score','affiliate_url','image_url','published_at')} for r in selected]}
    stamp = datetime.now(TZ).strftime('%Y%m%dT%H%M%S')
    out = OUT_DIR / f'weekly_summary_{stamp}.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(f'[WEEKLY] ventana={start_local:%Y-%m-%d}..{end_local:%Y-%m-%d} Europe/Madrid')
    print(f'[WEEKLY] publicaciones_candidatas={len(rows)} seleccionadas={len(selected)}')
    print(f'[WEEKLY] borrador={out}')
    print('\n--- TELEGRAM PREVIEW ---\n' + payload['telegram_html'])
    print('\n--- INSTAGRAM PREVIEW ---\n' + payload['instagram_caption'])
    print('\n[WEEKLY] MODO BORRADOR: no se publica ni se modifica ningún temporizador.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
