"""Recolector histórico de futuros canales. Nunca publica.
Cada ejecución añade/actualiza el producto y guarda una foto de precio por día.
"""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from datetime import datetime, timezone
from database import init_db, DB_PATH, upsert_product, save_price_snapshot
from channel_registry import planned_channels, categories_for_channel, get_channel
from sources.amazon import buscar as buscar_amazon, get_last_status as amazon_status
from sources.aliexpress import buscar as buscar_aliexpress, get_last_status as aliexpress_status

ROOT=Path(__file__).resolve().parent
CATALOG=ROOT/'config'/'channel_catalogs.json'
OUT=ROOT/'data'/'historical_channels.json'
LIMIT=5


def ensure_schema():
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        cols={r[1] for r in con.execute('PRAGMA table_info(products)')}
        if 'channel' not in cols: con.execute('ALTER TABLE products ADD COLUMN channel TEXT')
        if 'family' not in cols: con.execute('ALTER TABLE products ADD COLUMN family TEXT')
        con.execute('CREATE INDEX IF NOT EXISTS idx_products_channel ON products(channel)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_products_family ON products(family)')
        con.commit()


def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))['catalogs']


def tag_product(pid, channel, family):
    with sqlite3.connect(DB_PATH) as con:
        con.execute('UPDATE products SET channel=?, family=? WHERE id=?',(channel,family,pid))
        con.commit()


def collect():
    ensure_schema()
    catalogs=load_catalog()
    summary={'started_at':datetime.now(timezone.utc).isoformat(),'channels':{},'products_new_or_seen':0,'snapshots':0,'errors':0}
    for channel in planned_channels():
        conf=get_channel(channel); family=conf['family']
        categories=categories_for_channel(channel)
        summary['channels'][channel]={'family':family,'queries':0,'amazon':0,'aliexpress':0,'products':0,'errors':0}
        print(f'\n### {channel} / {family} ###', flush=True)
        for category in categories:
            queries=catalogs.get(channel,{}).get(category,[])
            if not queries: continue
            for q in queries:
                summary['channels'][channel]['queries']+=1
                for source, fn, status_fn in [('amazon',buscar_amazon,amazon_status),('aliexpress',buscar_aliexpress,aliexpress_status)]:
                    try:
                        found=fn(q,LIMIT,category=category)
                        summary['channels'][channel][source]+=len(found)
                        for offer in found:
                            pid=upsert_product(offer)
                            tag_product(pid,channel,family)
                            save_price_snapshot(pid,offer.current_price)
                            summary['channels'][channel]['products']+=1
                            summary['products_new_or_seen']+=1
                            summary['snapshots']+=1
                    except Exception as exc:
                        summary['channels'][channel]['errors']+=1; summary['errors']+=1
                        print(f'[WARN] {source} {channel}/{category}/{q}: {exc}',flush=True)
                print(f'[OK] {channel}/{category}: {q}',flush=True)
    summary['finished_at']=datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('\n=== HISTÓRICO FUTUROS CANALES ===')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': collect()
