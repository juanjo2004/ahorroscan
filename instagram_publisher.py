#!/usr/bin/env python3
import argparse, os, sqlite3, time, urllib.parse, urllib.request, json
from pathlib import Path
from redirector.link_manager import get_or_create_product_link

API_VERSION = os.getenv('INSTAGRAM_API_VERSION', 'v26.0')
GRAPH = f'https://graph.instagram.com/{API_VERSION}'
ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'instagram_publications.db'


def load_env():
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1)
            os.environ.setdefault(k,v)


def api(method, path, params=None):
    params = params or {}
    token=os.environ['INSTAGRAM_ACCESS_TOKEN']
    params['access_token']=token
    url=GRAPH+path
    if method=='GET':
        url += '?' + urllib.parse.urlencode(params)
        req=urllib.request.Request(url, method='GET')
    else:
        req=urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors='replace')
        raise RuntimeError(f'Instagram API HTTP {e.code}: {body}')


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(DB)
    con.execute('''CREATE TABLE IF NOT EXISTS instagram_publications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product_id INTEGER NOT NULL,
      source TEXT NOT NULL,
      external_id TEXT,
      title TEXT NOT NULL,
      image_url TEXT NOT NULL,
      affiliate_url TEXT,
      price REAL,
      discount_pct REAL,
      score REAL,
      media_id TEXT,
      status TEXT NOT NULL,
      published_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(product_id)
    )''')
    con.commit(); return con


def product(pid):
    con=sqlite3.connect(ROOT/'data/ofertas.db')
    p=con.execute('SELECT id,source,external_id,title,affiliate_url,image_url,rating,reviews,category FROM products WHERE id=?',(pid,)).fetchone()
    h=con.execute("SELECT price FROM price_history WHERE product_id=? AND origin='tech' ORDER BY id DESC LIMIT 1",(pid,)).fetchone()
    pub=con.execute("SELECT price,discount_pct,score FROM publications WHERE product_id=? AND origin='tech' ORDER BY id DESC LIMIT 1",(pid,)).fetchone()
    con.close()
    if not p: raise RuntimeError(f'Producto {pid} no existe')
    return p,h[0] if h else None,pub


def _format_eur(value):
    if value is None:
        return None
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _checked_at():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y · %H:%M")


def caption(p, price, pub):
    pid,source,external,title,affiliate,image,rating,reviews,category=p
    discount = pub[1] if pub else None
    reference = None
    if pub and pub[0] is not None and discount is not None and discount > 0:
        reference = pub[0] / (1 - discount / 100) if discount < 100 else None

    source_name = {"amazon": "Amazon", "aliexpress": "AliExpress"}.get(source, source or "Tienda")
    category_labels = {
        "mice": "🖱️ Ratones", "peripherals": "⌨️ Periféricos", "power": "🔋 Energía",
        "projectors": "📽️ Proyectores", "wearables": "⌚ Wearables", "monitors": "🖥️ Monitores",
        "storage": "💾 Almacenamiento", "smartphones": "📱 Smartphones",
    }
    lines = [
        f"🔥 SUPER OFERTA EN {source_name.upper()}",
        "",
        title[:180],
        "",
    ]
    if reference is not None:
        lines.append(f"💰 Precio normal: {_format_eur(reference)}")
    if price is not None:
        lines.append(f"🔥 Precio SUPER OFERTA: {_format_eur(price)}")
    if discount is not None:
        lines.append(f"📉 Descuento: {discount:.0f}%")
    lines.append("")
    if rating:
        quality = f"⭐ Puntuación: {rating:.1f}/5"
        if reviews is not None:
            quality += f" · ({reviews:,} valoraciones)".replace(",", ".")
        lines.append(quality)
    lines.append(category_labels.get(category, category or "Tecnología"))
    link = get_or_create_product_link(pid, affiliate, "instagram_tech", "instagram_post")
    lines += [
        "",
        f"🕒 Precio comprobado: {_checked_at()}",
        "",
        "🔗 ENLACE EN BIO:",
        "ahorroscan.es",
        "",
        "⚠️ Enlace de afiliado. Podemos recibir una comisión por compras que cumplan los requisitos, sin que el precio cambie.",
        "",
        "#AhorroScan #Ofertas #Chollos #Amazon #Tecnologia",
    ]
    return "\n".join(lines)


def main():
    load_env()
    ap=argparse.ArgumentParser()
    ap.add_argument('--product-id',type=int,required=True)
    ap.add_argument('--publish',action='store_true')
    args=ap.parse_args()
    ig=os.environ.get('INSTAGRAM_USER_ID')
    if not ig: raise RuntimeError('Falta INSTAGRAM_USER_ID')
    # Resolve the object ID used by the Instagram Login API from /me.
    me=api('GET','/me',{'fields':'id,user_id,username,name'})
    ig_object=me['id']
    p,price,pub=product(args.product_id)
    cap=caption(p,price,pub)
    print('Cuenta:',me.get('username'),'ID:',ig_object)
    print('Producto:',p[0],p[3])
    print('Precio:',price,'Descuento:',pub[1] if pub else None)
    print('Imagen:',p[5])
    print('CAPTION:\n'+cap)
    if not args.publish:
        print('DRY RUN: no se crea ni publica contenido.')
        return
    con=init_db()
    existing=con.execute('SELECT media_id,status FROM instagram_publications WHERE product_id=?',(args.product_id,)).fetchone()
    if existing and existing[1]=='PUBLISHED':
        raise RuntimeError(f'Producto ya publicado en Instagram: {existing[0]}')
    c=api('POST',f'/{ig_object}/media',{'image_url':p[5],'caption':cap})
    cid=c['id']; print('Container:',cid)
    for _ in range(20):
        st=api('GET',f'/{cid}',{'fields':'id,status_code,status'})
        print('Status:',st)
        if st.get('status_code')=='FINISHED': break
        if st.get('status_code') in ('ERROR','EXPIRED'): raise RuntimeError(f'Container no publicable: {st}')
        time.sleep(3)
    else: raise RuntimeError('Timeout esperando container')
    pubr=api('POST',f'/{ig_object}/media_publish',{'creation_id':cid})
    mid=pubr['id']; print('Published media:',mid)
    con.execute('INSERT OR REPLACE INTO instagram_publications(product_id,source,external_id,title,image_url,affiliate_url,price,discount_pct,score,media_id,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
      (p[0],p[1],p[2],p[3],p[5],p[4],price,pub[1] if pub else None,pub[2] if pub else None,mid,'PUBLISHED'))
    con.commit(); con.close()
    print('REGISTRO OK')

if __name__=='__main__': main()
