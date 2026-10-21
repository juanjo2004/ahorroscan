#!/usr/bin/env python3
"""Mide el rendimiento de campañas estacionales: publicaciones -> clics -> conversiones."""
from __future__ import annotations
import os
import json, sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
TECH_DB=ROOT/"data/ofertas.db"
HOGAR_DB=Path(os.environ.get('AHOROSCAN_GLOBAL_DB', str(ROOT / 'data' / 'ofertas.db')))
CLICKS_DB=ROOT/"redirector/clicks.db"
LEDGER=ROOT/"data/monetization.db"
OUT=ROOT/"data/seasonal_performance.json"
TZ=ZoneInfo("Europe/Madrid")

def con(p):
    c=sqlite3.connect(p); c.row_factory=sqlite3.Row; return c

def parse_dt(value):
    if not value: return None
    try:
        return datetime.fromisoformat(str(value).replace("Z","+00:00")).astimezone(TZ)
    except Exception:
        return None

def active_seasons(d):
    # Reuse the production calendar from each project.
    from seasonal_engine import active_seasons as tech_active
    from pathlib import Path as P
    import sys
    tech=[x for x in tech_active(d) if x]
    try:
        sys.path.insert(0, "/home/debian/ahorroscan/test/current/ahorroscan-hogar")
        from sources.seasonality import active_seasons as hogar_active
        hogar=[x for x in hogar_active(d) if x]
    except Exception:
        hogar=[]
    return sorted(set(tech+hogar))

def title_matches(title):
    t=(title or "").lower()
    keywords={
      "halloween":("halloween","calabaza","terror"),
      "black_friday":("black friday","cyber monday"),
      "christmas":("navidad","navide","papá noel","regalo navideño"),
      "new_year":("nochevieja","cotillón","cotillon"),
      "valentines":("san valentín","san valentin","romántic","romantic"),
      "fathers_day":("día del padre","dia del padre","papá","papa"),
      "easter":("pascua","primavera"),
      "mothers_day":("día de la madre","dia de la madre","mamá","mama"),
      "summer":("verano","piscina","terraza","jardín","jardin"),
    }
    return [name for name,terms in keywords.items() if any(x in t for x in terms)]

def publications():
    rows=[]
    with con(TECH_DB) as c:
        q="SELECT product_id,source,external_id,title,category,price,discount_pct AS discount,score,published_at FROM publications WHERE origin='tech'"
        for r in c.execute(q):
            d=dict(r); d["project"]="tech"; rows.append(d)
    with con(HOGAR_DB) as c:
        q="SELECT product_id,source,external_id,title,price,discount_percent AS discount,score,published_at FROM publications WHERE origin='hogar'"
        for r in c.execute(q):
            d=dict(r); d["project"]="hogar"; rows.append(d)
    return rows

def clicks_map():
    out=defaultdict(int)
    with con(CLICKS_DB) as c:
        for r in c.execute("SELECT project,product_id,COUNT(*) n FROM clicks_v3 GROUP BY project,product_id"):
            project=str(r["project"]); pid=int(r["product_id"])
            if project.startswith("instagram_"):
                base=project.removeprefix("instagram_")
                out[(base,pid)] += int(r["n"])
            out[(project,pid)] += int(r["n"])
    return out

def commission_rows():
    if not LEDGER.exists(): return []
    with con(LEDGER) as c:
        return [dict(r) for r in c.execute("SELECT * FROM commissions")]

def build():
    clicks=clicks_map()
    commissions=commission_rows()
    comm_by_product=defaultdict(float); tx_by_product=defaultdict(int)
    comm_by_season=defaultdict(float); tx_by_season=defaultdict(int)
    for r in commissions:
        pid=r.get("product_id")
        project=r.get("project")
        if pid is not None:
            key=(str(project or "unknown"), int(pid))
            comm_by_product[key] += float(r.get("commission") or 0)
            tx_by_product[key] += 1
        if r.get("season"):
            comm_by_season[str(r["season"])] += float(r.get("commission") or 0)
            tx_by_season[str(r["season"])] += 1

    campaign=defaultdict(lambda: {"publications":0,"clicks":0,"transactions":0,"commission":0.0,"products":[]})
    product_rows=[]
    for r in publications():
        dt=parse_dt(r["published_at"])
        seasons=set(title_matches(r["title"]))
        if dt:
            # Solo atribuimos la campaña si estaba activa en la fecha de publicación.
            seasons={s for s in seasons if s in active_seasons(dt.date())}
        if not seasons: continue
        cl=clicks.get((r["project"],int(r["product_id"])),0)
        key=(r["project"], int(r["product_id"]))
        tx=tx_by_product.get(key,0)
        commission=comm_by_product.get(key,0.0)
        for season in sorted(seasons):
            b=campaign[season]
            b["publications"]+=1; b["clicks"]+=cl; b["transactions"]+=tx; b["commission"]+=commission
            b["products"].append({"project":r["project"],"product_id":r["product_id"],"title":r["title"],"clicks":cl,"transactions":tx,"commission":round(commission,2),"published_at":r["published_at"]})
        product_rows.append({"project":r["project"],"product_id":r["product_id"],"title":r["title"],"seasons":sorted(seasons),"clicks":cl,"transactions":tx,"commission":round(commission,2)})

    for b in campaign.values():
        b["clicks_per_publication"]=round(b["clicks"]/b["publications"],3) if b["publications"] else 0
        b["commission_per_click"]=round(b["commission"]/b["clicks"],3) if b["clicks"] else 0
        b["commission_per_publication"]=round(b["commission"]/b["publications"],3) if b["publications"] else 0
        b["products"]=sorted(b["products"],key=lambda x:(-x["clicks"],-x["commission"]))[:20]

    data={"generated_at":datetime.now(timezone.utc).isoformat(),"campaigns":dict(sorted(campaign.items())),"products":product_rows,"notes":{"commission_attribution":"Solo exacta cuando el CSV de afiliado incluye product_id. Las comisiones sin product_id siguen en monetization.json, pero no se asignan a una campaña concreta."}}
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print("[SEASONAL PERFORMANCE] campañas:",len(campaign))
    for k,v in sorted(campaign.items(),key=lambda x:(-x[1]["commission"],-x[1]["clicks"])):
        print(f"  {k}: pubs={v['publications']} clicks={v['clicks']} tx={v['transactions']} comisión={v['commission']:.2f}€")

if __name__=="__main__":
    build()
