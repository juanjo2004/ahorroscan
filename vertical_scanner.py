from __future__ import annotations
import sys
from dedupe import product_key
from database import init_db,upsert_product,save_price_snapshot,get_history_stats
from scoring import score_offer,classify_offer
from sources.amazon import buscar as buscar_amazon
from sources.aliexpress import buscar as buscar_aliexpress
from vertical_channel import CHANNELS,select_vertical_publicable
from prime_day import PRIME_DAY_MODE, history_for

# The catalog file is JSON, so keep the scanner independent from config imports.
import json
from pathlib import Path
CATALOG_PATH=Path(__file__).resolve().parent/'config/channel_catalogs.json'

def _queries(channel,category):
    data=json.loads(CATALOG_PATH.read_text())
    return tuple(data['catalogs'].get(channel,{}).get(category,()))

def scan(channel):
    if channel not in CHANNELS: raise ValueError(f'Canal no soportado: {channel}')
    init_db(); candidates=[]
    for category in CHANNELS[channel]['categories']:
        for q in _queries(channel,category):
            for name,fn in (('Amazon',buscar_amazon),('AliExpress',buscar_aliexpress)):
                try:
                    candidates.extend(fn(q, __import__('config').MAX_PRODUCTS_PER_QUERY, category=category))
                except Exception as exc:
                    print(f'[VERTICAL-SCANNER] {channel} {name} {category} {q!r}: {type(exc).__name__}: {exc}')
    unique={}
    for offer in candidates:
        key=product_key(offer)
        if key not in unique: unique[key]=offer
    scored=[]
    for offer in unique.values():
        pid=upsert_product(offer); offer.product_id=pid
        history=get_history_stats(pid,30)
        history=history_for(history)
        score,breakdown=score_offer(offer,history)
        classification=classify_offer(score,offer)
        save_price_snapshot(pid,offer.current_price)
        scored.append((score,offer,history,breakdown,classification))
    publicable=select_vertical_publicable(scored,channel)
    print(f'[VERTICAL-SCANNER] {channel}: candidatas={len(candidates)} unicas={len(unique)} publicables={len(publicable)}')
    for i,row in enumerate(publicable,1):
        score,offer,history,breakdown,classification=row
        print(f'{i:02d}. [{offer.category}] [{score:.1f}] {offer.source}:{offer.external_id} {offer.title[:100]}')
    return scored,publicable

if __name__=='__main__':
    scan(sys.argv[1] if len(sys.argv)>1 else 'moda')