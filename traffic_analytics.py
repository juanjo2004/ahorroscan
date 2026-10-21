#!/usr/bin/env python3
import json, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DB=ROOT/"redirector"/"clicks.db"
OUT=ROOT/"data"/"traffic_analytics.json"
SYNTH=("AhorroScan-Test","AhorroScan-Smoke","curl/","python-requests/")

def q(con, sql, args=()):
    return con.execute(sql,args).fetchall()

def main():
    now=datetime.now(timezone.utc); cutoff=(now-timedelta(days=30)).isoformat()
    with sqlite3.connect(DB) as c:
        c.row_factory=sqlite3.Row
        tables={r[0] for r in q(c,"select name from sqlite_master where type='table'")}
        pageviews=q(c,"select path,country,device,browser,referrer,utm_source,utm_medium,utm_campaign from pageviews where viewed_at>=?",(cutoff,)) if "pageviews" in tables else []
        clicks=q(c,"select project,product_id,channel,clicked_at,user_agent,country,device,browser,referrer from clicks_v3 where clicked_at>=?",(cutoff,)) if "clicks_v3" in tables else []
    real=[r for r in clicks if not any(x in (r["user_agent"] or "") for x in SYNTH)]
    def count(rows,key):
        d={}
        for r in rows: d[str(r[key] or "unknown")]=d.get(str(r[key] or "unknown"),0)+1
        return sorted(({"value":k,"count":v} for k,v in d.items()),key=lambda x:(-x["count"],x["value"]))
    data={
      "generated_at":now.isoformat(),"window_days":30,
      "pageviews":{"total":len(pageviews),"by_path":count(pageviews,"path"),"by_country":count(pageviews,"country"),"by_device":count(pageviews,"device"),"by_browser":count(pageviews,"browser"),"by_utm_source":count(pageviews,"utm_source"),"by_utm_medium":count(pageviews,"utm_medium")},
      "qualified_offer_clicks":{"total":len(real),"by_project":count(real,"project"),"by_channel":count(real,"channel"),"by_country":count(real,"country"),"by_device":count(real,"device"),"by_browser":count(real,"browser")},
      "instagram":{"tracked_offer_clicks":sum(1 for r in real if str(r["project"]).startswith("instagram_")),"note":"Instagram Insights supplies views/reach/interactions; this section supplies clicks from the Instagram landing/profile path."},
      "telegram":{"tracked_offer_clicks":sum(1 for r in real if str(r["channel"] or "").startswith("telegram_")),"note":"Telegram Bot API does not expose channel-post view counts. Offer clicks are measured through AhorroScan tracking links."}
    }
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
