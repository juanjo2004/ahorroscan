from __future__ import annotations

import os

import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TECH_DB = ROOT / "data" / "ofertas.db"
HOGAR_DB = Path(os.environ.get('AHOROSCAN_GLOBAL_DB', str(ROOT / 'data' / 'ofertas.db')))
CLICKS_DB = ROOT / "redirector" / "clicks.db"
INSTAGRAM_DB = ROOT / "data" / "instagram_publications.db"
EDITORIAL_DB = ROOT / "data" / "instagram_content.db"
OUT = ROOT / "data" / "performance.json"
REAL_START_FILE = ROOT / "data" / "REAL_TRAFFIC_START.txt"


def con(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def clicks():
    out = {}
    if CLICKS_DB.exists():
        try:
            real_start=REAL_START_FILE.read_text().strip()
        except Exception:
            real_start="9999-01-01T00:00:00+00:00"
        with con(CLICKS_DB) as c:
            for r in c.execute("SELECT project,product_id,COUNT(*) clicks FROM clicks_v3 WHERE clicked_at>=? AND LOWER(COALESCE(user_agent,'')) NOT LIKE '%ahorroscan-test%' AND LOWER(COALESCE(user_agent,'')) NOT LIKE '%ahorroscan-smoke%' AND LOWER(COALESCE(user_agent,'')) NOT LIKE '%ahoroscan-test%' AND LOWER(COALESCE(user_agent,'')) NOT LIKE '%ahoroscan-smoke%' AND LOWER(COALESCE(user_agent,'')) NOT LIKE 'curl/%' AND LOWER(COALESCE(user_agent,'')) NOT LIKE 'python-requests/%' GROUP BY project,product_id",(real_start,)):
                project=str(r["project"]); pid=int(r["product_id"]); n=int(r["clicks"])
                out[(project,pid)] = n
                if project == "instagram_tech": out[("tech",pid)] = out.get(("tech",pid),0) + n
                elif project == "instagram_hogar": out[("hogar",pid)] = out.get(("hogar",pid),0) + n
    return out

def instagram_stats():
    out = {}
    if INSTAGRAM_DB.exists():
        with con(INSTAGRAM_DB) as c:
            for r in c.execute("SELECT product_id,COUNT(*) publications FROM instagram_publications WHERE status='PUBLISHED' GROUP BY product_id"):
                out[int(r["product_id"])] = int(r["publications"])
    return out


def editorial_stats():
    result = {"publications": 0, "views": 0, "reach": 0, "likes": 0, "comments": 0,
              "shares": 0, "saves": 0, "total_interactions": 0, "by_content_type": {}}
    if not EDITORIAL_DB.exists():
        return result
    with con(EDITORIAL_DB) as c:
        rows = c.execute(
            "SELECT content_type, views, reach, likes, comments, shares, saves, total_interactions "
            "FROM editorial_publications WHERE status='PUBLISHED'"
        ).fetchall()
    for r in rows:
        result["publications"] += 1
        for key in ("views", "reach", "likes", "comments", "shares", "saves", "total_interactions"):
            result[key] += int(r[key] or 0)
        bucket = result["by_content_type"].setdefault(r["content_type"], {
            "publications": 0, "views": 0, "reach": 0, "likes": 0,
            "comments": 0, "shares": 0, "saves": 0, "total_interactions": 0,
        })
        bucket["publications"] += 1
        for key in ("views", "reach", "likes", "comments", "shares", "saves", "total_interactions"):
            bucket[key] += int(r[key] or 0)
    def rates(bucket):
        reach=bucket.get("reach",0)
        views=bucket.get("views",0)
        interactions=bucket.get("total_interactions",0)
        bucket["engagement_rate"]=round(interactions/reach,4) if reach else 0.0
        bucket["views_per_reach"]=round(views/reach,3) if reach else 0.0
    rates(result)
    for bucket in result["by_content_type"].values():
        rates(bucket)
    return result


def collect(days=30):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    rows=[]; cl=clicks(); ig=instagram_stats()
    with con(TECH_DB) as c:
        q="""SELECT p.product_id,p.source,p.external_id,p.title,p.category,p.price,p.discount_pct discount,p.score,p.published_at,pr.rating,pr.reviews FROM publications p LEFT JOIN products pr ON pr.id=p.product_id WHERE p.origin='tech' AND p.published_at>=?"""
        for r in c.execute(q,(cutoff,)):
            d=dict(r); d["project"]="tech"; d["clicks"]=cl.get(("tech",int(r["product_id"] or 0)),0); d["instagram_publications"]=ig.get(int(r["product_id"] or 0),0); rows.append(d)
    with con(HOGAR_DB) as c:
        q="""SELECT p.product_id,p.source,p.external_id,p.title,pr.category,p.price,p.discount_percent discount,p.score,p.published_at,pr.rating,pr.reviews FROM publications p LEFT JOIN products pr ON pr.id=p.product_id WHERE p.origin='hogar' AND p.published_at>=?"""
        for r in c.execute(q,(cutoff,)):
            d=dict(r); d["project"]="hogar"; d["clicks"]=cl.get(("hogar",int(r["product_id"] or 0)),0); d["instagram_publications"]=ig.get(int(r["product_id"] or 0),0); rows.append(d)
    return rows
def build(days=30):
    rows=collect(days)
    products=[]; categories={}; projects={}; sources={}
    editorial=editorial_stats()
    for r in rows:
        products.append({
            "project":r["project"],"source":r["source"],"product_id":r["product_id"],
            "external_id":r["external_id"],"title":r["title"],"category":r["category"],
            "price":r["price"],"discount":r["discount"],"score":r["score"],
            "rating":r["rating"],"reviews":r["reviews"],"published_at":r["published_at"],"clicks":r["clicks"],"instagram_publications":r.get("instagram_publications",0)
        })
        key=(r["project"],r["category"] or "otros")
        bucket=categories.setdefault(key,{"publications":0,"clicks":0,"score_sum":0.0})
        bucket["publications"]+=1; bucket["clicks"]+=r["clicks"]; bucket["instagram_publications"]=bucket.get("instagram_publications",0)+r.get("instagram_publications",0); bucket["score_sum"]+=float(r["score"] or 0)
        key=r["project"]; bucket=projects.setdefault(key,{"publications":0,"clicks":0,"score_sum":0.0}); bucket["publications"]+=1; bucket["clicks"]+=r["clicks"]; bucket["instagram_publications"]=bucket.get("instagram_publications",0)+r.get("instagram_publications",0); bucket["score_sum"]+=float(r["score"] or 0)
        key=r["source"]; bucket=sources.setdefault(key,{"publications":0,"clicks":0}); bucket["publications"]+=1; bucket["clicks"]+=r["clicks"]
    for b in list(categories.values())+list(projects.values()):
        b["ctr_proxy"]=round(b["clicks"]/b["publications"],3) if b["publications"] else 0
        if "instagram_publications" in b: b["instagram_rate"]=round(b["instagram_publications"]/b["publications"],3) if b["publications"] else 0
        b["avg_score"]=round(b["score_sum"]/b["publications"],2) if b["publications"] else 0
        b.pop("score_sum",None)
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"window_days":days,"products":products,"categories":{f"{k[0]}::{k[1]}":v for k,v in categories.items()},"projects":projects,"sources":sources,"instagram_editorial":editorial}


def main():
    data=build(30); OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(f"[PERFORMANCE] products={len(data['products'])} projects={data['projects']}")
    print("[PERFORMANCE] categories:")
    for k,v in sorted(data["categories"].items(),key=lambda x:(-x[1]["clicks"],-x[1]["avg_score"]))[:15]: print(k,v)

if __name__=="__main__": main()
