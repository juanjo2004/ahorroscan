import os
#!/usr/bin/env python3
"""Informe de conversión de los enlaces de Instagram medibles en AhorroScan."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).resolve().parent
DB=ROOT/'redirector'/'clicks.db'
IG=ROOT/'data'/'instagram_publications.db'
TECH=ROOT/'data'/'ofertas.db'
HOGAR=Path(os.environ.get('AHOROSCAN_GLOBAL_DB', str(ROOT / 'data' / 'ofertas.db')))

def c(p):
 x=sqlite3.connect(p); x.row_factory=sqlite3.Row; return x

def main():
 now=datetime.now(timezone.utc); cutoff=(now-timedelta(days=30)).isoformat()
 with c(DB) as db:
  total=db.execute("select count(*) n from clicks_v3 where project like 'instagram_%' and clicked_at>=?",(cutoff,)).fetchone()['n']
  rows=db.execute("""select project,count(*) clicks from clicks_v3 where project like 'instagram_%' and clicked_at>=? group by project order by clicks desc""",(cutoff,)).fetchall()
  products=db.execute("""select project,product_id,count(*) clicks from clicks_v3 where project like 'instagram_%' and clicked_at>=? group by project,product_id order by clicks desc limit 20""",(cutoff,)).fetchall()
 print(f'[INSTAGRAM-CONVERSION] ventana=30d clicks_trackeables={total}')
 for r in rows: print(f'  {r["project"]}: {r["clicks"]} clicks')
 print('[INSTAGRAM-CONVERSION] top productos:')
 for r in products: print(f'  {r["project"]} product={r["product_id"]}: {r["clicks"]} clicks')
 with c(IG) as db:
  published=db.execute("select count(*) n from instagram_publications where status='PUBLISHED' and published_at>=?",(cutoff,)).fetchone()['n']
 print(f'[INSTAGRAM-CONVERSION] publicaciones={published}')
 print('[INSTAGRAM-CONVERSION] Nota: Amazon se mide mediante GA4 porque los enlaces permanecen directos; AliExpress se mide además mediante redirector.')

if __name__=='__main__': main()
