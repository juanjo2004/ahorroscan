#!/usr/bin/env python3
from __future__ import annotations
import os
import sqlite3, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path('/home/debian/ahorroscan/test/current/telegram-bot-v2')
AGG=ROOT/'data/aggregator.db'; TECH=ROOT/'data/ofertas.db'
HOGAR=Path(os.environ.get('AHOROSCAN_GLOBAL_DB', str(ROOT / 'data' / 'ofertas.db')))
OUT=Path('/home/debian/ahorroscan/test/current/superofertastech-web/instagram/generated'); OUT.mkdir(parents=True,exist_ok=True)
IGDB=ROOT/'data/instagram_publications.db'
CONTENT_DB=ROOT/'data/instagram_content.db'
IG_ALLOWED_CATEGORIES={'seasonal_halloween','smartphones','tablets','laptops','monitors','televisores','gaming','wearables','audio','storage','desktops','mice','keyboards','peripherals','microphones','projectors','drones','networking','charging','power','home_security','cleaning','kitchen','tools','climate'}
IG_TITLE_BLOCKLIST=('guirnalda','hojas de','banner','carta de aceptación','carta de aceptacion','suministro de fiesta','navideña','navideno','navideño')
def instagram_candidate_ok(row):
 cat=(row.get('category') or '').strip().lower()
 title=(row.get('title') or '').lower()
 if cat not in IG_ALLOWED_CATEGORIES: return False
 if any(term in title for term in IG_TITLE_BLOCKLIST): return False
 category_terms={'storage':('ssd','nvme','hdd','disco duro','memoria','tarjeta de memoria'),'projectors':('proyector','projector'),'networking':('router','wifi','wi-fi','switch','ethernet','network')}
 required=category_terms.get(cat)
 return not required or any(term in title for term in required)

def db(p):
 c=sqlite3.connect(p); c.row_factory=sqlite3.Row; return c
def eur(v): return f'{float(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')+' €'
def font(n,b=False):
 p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if b else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
 return ImageFont.truetype(p,n)
def resolve(r):
 for path,dc in ((TECH,'discount_pct'),(HOGAR,'discount_percent')):
  if not path.exists(): continue
  with db(path) as c:
   q=c.execute(f'''SELECT pr.title,pr.image_url,pr.affiliate_url,pr.rating,pr.reviews,pr.category,p.price,p.{dc} AS discount
                   FROM products pr JOIN publications p ON p.product_id=pr.id
                   WHERE pr.id=? AND pr.source=? AND pr.external_id=?
                     AND p.origin = ?
                   ORDER BY p.id DESC LIMIT 1''',
               (r['product_id'],r['source'],r['external_id'], 'tech' if path == TECH else 'hogar')).fetchone()
  if q:
   d=dict(q); d.update(dict(r)); d['project_origin']='tech' if path==TECH else 'hogar'; return d
 return None
def wrap(d,text,f,maxw):
 out=[]; cur=''
 for w in text.split():
  t=(cur+' '+w).strip()
  if d.textbbox((0,0),t,font=f)[2]<=maxw: cur=t
  else:
   if cur: out.append(cur)
   cur=w
 if cur: out.append(cur)
 return out
def init_content_db():
 with db(CONTENT_DB) as c:
  c.execute('''CREATE TABLE IF NOT EXISTS editorial_publications(
   id INTEGER PRIMARY KEY AUTOINCREMENT, content_type TEXT NOT NULL,
   image_path TEXT NOT NULL, public_url TEXT NOT NULL, caption TEXT NOT NULL,
   status TEXT NOT NULL DEFAULT 'GENERATED', media_id TEXT, generated_at TEXT NOT NULL,
   published_at TEXT, impressions INTEGER, reach INTEGER, likes INTEGER,
   comments INTEGER, shares INTEGER, saves INTEGER)''')
  c.commit()

def daily_count():
 day=datetime.now(timezone.utc).date().isoformat()
 with db(CONTENT_DB) as c:
  return c.execute("SELECT COUNT(*) FROM editorial_publications WHERE status='PUBLISHED' AND substr(published_at,1,10)=?",(day,)).fetchone()[0]

def main():
 init_content_db()
 if daily_count() >= 1:
  print('[INSTAGRAM-CONTENT] límite editorial diario alcanzado'); return
 with db(AGG) as c:
  rows=c.execute("""SELECT source,external_id,product_id,title,category,score,published_at
                    FROM aggregator_publications WHERE project='central'
                    ORDER BY score DESC,published_at DESC,id DESC LIMIT 40""").fetchall()
 offers=[]; seen=set()
 for r in rows:
  k=(r['source'],r['external_id'],r['product_id'])
  if k in seen: continue
  p=resolve(r)
  if not p or not p.get('image_url') or not p.get('affiliate_url'): continue
  if not instagram_candidate_ok(p): continue
  seen.add(k); offers.append(p)
  if len(offers)==3: break
 if len(offers)<3: raise SystemExit('No hay 3 ofertas válidas')
 W,H=1080,1350; im=Image.new('RGB',(W,H),'#f6f7fb'); d=ImageDraw.Draw(im)
 d.rounded_rectangle((36,32,W-36,H-32),34,fill='white',outline='#dbe2ea',width=3)
 d.text((72,65),'🔥 AhorroScan',font=font(54,True),fill='#111827')
 d.text((72,130),'3 oportunidades encontradas hoy',font=font(30),fill='#374151')
 y=205
 for i,o in enumerate(offers,1):
  d.rounded_rectangle((64,y,W-64,y+320),24,fill='#f8fafc')
  try:
   req=urllib.request.Request(o['image_url'],headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=20) as resp: pic=Image.open(resp).convert('RGB')
   pic.thumbnail((250,250)); im.paste(pic,(85+(250-pic.width)//2,y+35+(250-pic.height)//2))
  except Exception: pass
  f=font(27,True); x=365
  d.text((x,y+30),f'{i:02d}  '+('🏠 Hogar' if o['project_origin']=='hogar' else '💻 Tech'),font=f,fill='#4f46e5')
  yy=y+72
  for line in wrap(d,o['title'][:105],f,W-x-90)[:3]:
   d.text((x,yy),line,font=f,fill='#111827'); yy+=35
  d.text((x,yy+10),eur(o['price']),font=font(38,True),fill='#111827')
  if o.get('discount'): d.text((x,yy+60),f'-{float(o["discount"]):.0f}%',font=font(23),fill='#166534')
  y+=350
 d.text((72,H-85),'Escaneamos miles de oportunidades. Tú solo ves las que merecen la pena.',font=font(22),fill='#475569')
 stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'); path=OUT/f'top3_{stamp}.jpg'; im.save(path,quality=90,optimize=True)
 public=f'https://ahorroscan.es/instagram/generated/{path.name}'
 caption='🔥 3 oportunidades que AhorroScan ha encontrado hoy\n\n'
 for i,o in enumerate(offers,1):
  src={'amazon':'Amazon','aliexpress':'AliExpress'}.get(o['source'],o['source'])
  caption+=f'{i}. {o["title"][:140]}\n💰 {eur(o["price"])}'
  if o.get('discount'): caption+=f' · -{float(o["discount"]):.0f}%'
  caption+=f' · {src}\n'
 caption+='\n🔗 Mira las ofertas: enlace en la bio → ahorroscan.es/instagram/\n\n⚠️ Algunos enlaces son de afiliado. Podemos recibir una comisión sin que el precio cambie.\n\n#AhorroScan #Ofertas #Chollos #Tecnologia #Hogar'
 now=datetime.now(timezone.utc).isoformat()
 with db(CONTENT_DB) as c:
  c.execute('INSERT INTO editorial_publications(content_type,image_path,public_url,caption,status,generated_at) VALUES(?,?,?,?,?,?)',('top3',str(path),public,caption,'GENERATED',now)); c.commit()
 print(f'[INSTAGRAM-CONTENT] generated={path}'); print(f'[INSTAGRAM-CONTENT] public_url={public}'); print(caption)
if __name__=='__main__': main()

