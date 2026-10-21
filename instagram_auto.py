#!/usr/bin/env python3
"""Publicación automática de AhorroScan en Instagram a partir del agregador central."""
from __future__ import annotations
import os
import argparse, html, hashlib, os, sqlite3, time, urllib.parse, urllib.request, json
from datetime import datetime, timezone
from pathlib import Path
from ha_publish_guard import deny_reason, publishing_enabled
from redirector.link_manager import get_or_create_product_link
from product_relevance import is_repair_related

ROOT=Path(__file__).resolve().parent
AGG=ROOT/'data'/'aggregator.db'
TECH=ROOT/'data'/'ofertas.db'
HOGAR=Path(os.environ.get('AHOROSCAN_GLOBAL_DB', str(ROOT / 'data' / 'ofertas.db')))
IGDB=ROOT/'data'/'instagram_publications.db'
RATE_LIMIT_STATE=ROOT/'data'/'instagram_rate_limit.json'
RATE_LIMIT_COOLDOWN_SECONDS=24*60*60
API_VERSION=os.getenv('INSTAGRAM_API_VERSION','v26.0')
GRAPH=f'https://graph.instagram.com/{API_VERSION}'
MAX_PER_RUN=int(os.getenv('INSTAGRAM_MAX_PER_RUN','1'))
MAX_PER_DAY=int(os.getenv('INSTAGRAM_MAX_PER_DAY','8'))
IG_ALLOWED_CATEGORIES={
 'smartphones','tablets','laptops','monitors','televisores','gaming','wearables','audio','storage','desktops',
 'mice','keyboards','peripherals','microphones','projectors','drones','networking','charging','power','home_security',
 'cleaning','kitchen','tools','climate'
}
IG_TITLE_BLOCKLIST=('hojas de','carta de aceptación','carta de aceptacion','suministro de fiesta','navideña','navideno','navideño')

def instagram_candidate_ok(row):
    cat=(row.get('category') or '').strip().lower()
    title=(row.get('title') or '').lower()
    # El canal general ya es la capa de curación. Instagram no limita por
    # familia para no excluir Móviles, Mascotas, Moda o Deportes.
    if not cat:
        return False
    if is_repair_related(title):
        return False
    if any(term in title for term in IG_TITLE_BLOCKLIST):
        return False
    category_terms={
      'storage':('ssd','nvme','hdd','disco duro','memoria','tarjeta de memoria'),
      'projectors':('proyector','projector'),
      'networking':('router','wifi','wi-fi','switch','ethernet','network'),
    }
    required=category_terms.get(cat)
    if required and not any(term in title for term in required):
        return False
    return True



def load_env():
    p=ROOT/'.env'
    if p.exists():
        for line in p.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1); os.environ.setdefault(k,v)


def db(path):
    c=sqlite3.connect(path); c.row_factory=sqlite3.Row; return c


def init_db():
    IGDB.parent.mkdir(parents=True,exist_ok=True)
    with db(IGDB) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS instagram_publications(
          id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
          source TEXT NOT NULL, external_id TEXT, title TEXT NOT NULL,
          image_url TEXT NOT NULL, affiliate_url TEXT, price REAL,
          discount_pct REAL, score REAL, media_id TEXT, status TEXT NOT NULL,
          published_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(product_id))''')


def daily_count():
    day=datetime.now(timezone.utc).date().isoformat()
    with db(IGDB) as c:
        return c.execute("SELECT COUNT(*) FROM instagram_publications WHERE status='PUBLISHED' AND substr(published_at,1,10)=?",(day,)).fetchone()[0]


def rate_limit_remaining(now=None):
    """Seconds remaining in the local cooldown after a Meta request-limit block."""
    now = now or datetime.now(timezone.utc)
    try:
        data=json.loads(RATE_LIMIT_STATE.read_text(encoding='utf-8'))
        until=datetime.fromisoformat(data['retry_after'])
        if until.tzinfo is None:
            until=until.replace(tzinfo=timezone.utc)
        return max(0, int((until-now).total_seconds()))
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def record_rate_limit(message):
    """Persist a conservative cooldown; never hammer Graph API after HTTP 403/limit."""
    now=datetime.now(timezone.utc)
    until=now+__import__('datetime').timedelta(seconds=RATE_LIMIT_COOLDOWN_SECONDS)
    RATE_LIMIT_STATE.parent.mkdir(parents=True,exist_ok=True)
    tmp=RATE_LIMIT_STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps({
        'reason':'meta_application_request_limit',
        'blocked_at':now.isoformat(),
        'retry_after':until.isoformat(),
        'detail':str(message)[:500],
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(RATE_LIMIT_STATE)
    return until


def is_meta_rate_limit(message):
    text=str(message).lower()
    return ('application request limit reached' in text or
            '2207051' in text or
            ('instagram api http 403' in text and 'request limit' in text))


def candidates():
    with db(AGG) as c:
        rows=c.execute('''SELECT project,channel,source,external_id,product_id,title,category,score,published_at
                          FROM aggregator_publications WHERE project='central'
                          ORDER BY score DESC,published_at DESC''').fetchall()
    out=[]
    for r in rows:
        with db(IGDB) as c:
            if c.execute('SELECT 1 FROM instagram_publications WHERE product_id=? AND status="PUBLISHED"',(r['product_id'],)).fetchone(): continue
        source=r['source']; p=None; resolved_channel=r['channel']
        vertical_tables={
            'moviles':'mobile_publications', 'mascotas':'pet_publications',
            'moda':'fashion_publications', 'deportes':'sports_publications',
        }
        # Las nuevas filas centrales llevan el canal de origen. Resolvemos en
        # su tabla real para no convertir, por ejemplo, Mascotas en "Tech"
        # solo porque ambas usan la misma DB física.
        if resolved_channel in vertical_tables:
            table=vertical_tables[resolved_channel]
            rating_cols = "rating, reviews" if resolved_channel in {"moda", "deportes"} else "NULL AS rating, NULL AS reviews"
            with db(TECH) as c:
                p=c.execute(f'''SELECT product_id id,source,external_id,title,affiliate_url,image_url,
                                       {rating_cols},
                                       category,price,discount_pct AS discount
                                FROM {table}
                                WHERE product_id=? AND source=? AND external_id=?
                                ORDER BY id DESC LIMIT 1''',(r['product_id'],r['source'],r['external_id'])).fetchone()
        else:
            # Compatibilidad con publicaciones centrales antiguas, anteriores
            # a la columna channel.
            for path in (TECH,HOGAR):
                if not path.exists(): continue
                discount_col = 'p.discount_pct' if path == TECH else 'p.discount_percent'
                origin = 'tech' if path == TECH else 'hogar'
                with db(path) as c:
                    p=c.execute(f'''SELECT pr.id,pr.source,pr.external_id,pr.title,pr.affiliate_url,pr.image_url,pr.rating,pr.reviews,
                                          pr.category,p.price,{discount_col} AS discount
                                   FROM products pr LEFT JOIN publications p ON p.product_id=pr.id
                                   WHERE pr.id=? AND pr.source=? AND pr.external_id=?
                                     AND p.origin = ?
                                   ORDER BY p.id DESC LIMIT 1''',(r['product_id'],r['source'],r['external_id'],origin)).fetchone()
                if p:
                    resolved_channel=origin
                    break
        if not p or not p['image_url'] or not p['affiliate_url']: continue
        candidate=dict(r); candidate.update(dict(p))
        if not instagram_candidate_ok(candidate): continue
        candidate['project_origin']=resolved_channel or 'central'
        candidate['project_db']=str(TECH if resolved_channel in vertical_tables else (HOGAR if resolved_channel=='hogar' else TECH))
        out.append(candidate)
    return out


def api(method,path,params):
    params=dict(params); params['access_token']=os.environ['INSTAGRAM_ACCESS_TOKEN']
    url=GRAPH+path
    if method=='GET':
        req=urllib.request.Request(url+'?'+urllib.parse.urlencode(params),method='GET')
    else:
        req=urllib.request.Request(url,data=urllib.parse.urlencode(params).encode(),method=method)
    try:
        with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e: raise RuntimeError(f'Instagram API HTTP {e.code}: {e.read().decode(errors="replace")}')


def eur(v):
    if v is None: return None
    return f'{v:,.2f}'.replace(',','X').replace('.',',').replace('X','.')+' €'


def caption(r):
    source={'amazon':'Amazon','aliexpress':'AliExpress'}.get(r['source'],r['source'] or 'Tienda')
    price=r['price']; discount=r['discount']
    # No inventamos un "precio normal" reconstruyéndolo desde el descuento.
    # Solo lo mostraríamos si la fuente proporcionara explícitamente ese dato.
    reference=None
    cat=r['category'] or ('Hogar' if r['project_origin']=='hogar' else 'Tecnología')
    cat_labels={'mice':'🖱️ Ratones','peripherals':'⌨️ Periféricos','power':'🔋 Energía','projectors':'📽️ Proyectores','wearables':'⌚ Wearables','monitors':'🖥️ Monitores','storage':'💾 Almacenamiento','smartphones':'📱 Smartphones','audio':'🎧 Audio','drones':'🚁 Drones','networking':'🌐 Networking','charging':'🔌 Carga','lighting':'💡 Iluminación','cleaning':'🧹 Limpieza','kitchen':'🍳 Cocina','tools':'🔧 Herramientas','garden':'🌱 Jardín','bathroom':'🛁 Baño','furniture':'🛋️ Muebles','textiles':'🛏️ Textil hogar','organization':'📦 Organización','climate':'🌬️ Climatización','home_security':'🔐 Seguridad hogar'}
    section_labels={
        'hogar':'🏠 HOGAR', 'moviles':'📱 MÓVILES', 'mascotas':'🐾 MASCOTAS',
        'moda':'👗 MODA', 'deportes':'🏃 DEPORTES', 'tech':'💻 TECH',
    }
    section=section_labels.get(r['project_origin'],'⭐ AHOROSCAN')
    lines=[f'🔥 SUPER OFERTA EN {source.upper()}', f'{section}','',r['title'][:180],'']
    if reference: lines.append(f'💰 Precio normal: {eur(reference)}')
    lines.append(f'🔥 Precio SUPER OFERTA: {eur(price)}')
    if discount: lines.append(f'📉 Descuento: {float(discount):.0f}%')
    lines.append('')
    if r['rating']:
        q=f'⭐ Puntuación: {float(r["rating"]):.1f}/5'
        if r['reviews']: q+=f' · ({int(r["reviews"]):,} valoraciones)'.replace(',','.')
        lines.append(q)
    link=get_or_create_product_link(r['product_id'], r['affiliate_url'], f'instagram_{r["project_origin"]}', 'instagram_post')
    channel_hashtags={
        'hogar':'#AhorroScan #AhorroScanHogar #Ofertas #Chollos #Hogar',
        'moviles':'#AhorroScan #AhorroScanMoviles #Ofertas #Chollos #Moviles',
        'mascotas':'#AhorroScan #AhorroScanMascotas #Ofertas #Chollos #Mascotas',
        'moda':'#AhorroScan #AhorroScanModa #Ofertas #Chollos #Moda',
        'deportes':'#AhorroScan #AhorroScanDeportes #Ofertas #Chollos #Deportes',
    }
    hashtags=channel_hashtags.get(r['project_origin'], '#AhorroScan #Ofertas #Chollos #AliExpress #Tecnologia' if r['source']=='aliexpress' else '#AhorroScan #Ofertas #Chollos #Amazon #Tecnologia')
    lines += [cat_labels.get(cat,'🗂️ '+str(cat)),'',f'🕒 Precio comprobado: {datetime.now().astimezone().strftime("%d/%m/%Y · %H:%M")}','','🔗 ENLACE EN BIO:','ahorroscan.es','', '⚠️ Enlace de afiliado. Podemos recibir una comisión por compras que cumplan los requisitos, sin que el precio cambie.','',hashtags]
    return '\n'.join(lines)


def instagram_image_url(r):
    """Return a public 4:5 image URL, padding the source without distortion.
    Instagram rejects source images outside its supported portrait ratio.
    Generated assets are cached in the public web root so Graph API can fetch them.
    """
    from PIL import Image
    media_dir=ROOT.parent/'superofertastech-web'/'instagram-media'
    media_dir.mkdir(parents=True,exist_ok=True)
    source_url=r['image_url']
    key=hashlib.sha256(source_url.encode()).hexdigest()[:20]
    out=media_dir/f'{key}.jpg'
    if not out.exists():
        req=urllib.request.Request(source_url, headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36','Referer':'https://www.aliexpress.com/'})
        raw=urllib.request.urlopen(req,timeout=30).read()
        from io import BytesIO
        try:
            src_ctx=Image.open(BytesIO(raw))
        except Exception as exc:
            from PIL import UnidentifiedImageError
            if isinstance(exc, UnidentifiedImageError):
                raise RuntimeError(f'Candidate image invalid: {exc}') from exc
            raise
        with src_ctx as src:
            src=src.convert('RGB')
            tw,th=1080,1350
            # Keep the product image intact, but reserve a visible CTA band at the bottom.
            banner_h=210
            area_h=th-banner_h
            scale=min(tw/src.width,area_h/src.height)
            size=(max(1,round(src.width*scale)),max(1,round(src.height*scale)))
            resized=src.resize(size,Image.Resampling.LANCZOS)
            canvas=Image.new('RGB',(tw,th),'white')
            canvas.paste(resized,((tw-size[0])//2,(area_h-size[1])//2))
            from PIL import ImageDraw, ImageFont
            draw=ImageDraw.Draw(canvas)
            y=area_h
            draw.rectangle((0,y,tw,th),fill=(18,18,18))
            try:
                bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',62)
                small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',30)
            except Exception:
                bold=small=None
            cta='🔗  ENLACE EN BIO'
            url='ahorroscan.es'
            # DejaVu may not contain the cart glyph, so fall back gracefully.
            if bold:
                try: draw.text((tw//2,y+28),cta,font=bold,anchor='ma',fill='white')
                except Exception: draw.text((tw//2,y+28),'ENLACE EN BIO',font=bold,anchor='ma',fill='white')
                draw.text((tw//2,y+105),url,font=small,anchor='ma',fill='white')
            else:
                draw.text((tw//2,y+35),'ENLACE EN BIO',fill='white')
                draw.text((tw//2,y+110),url,fill='white')
            canvas.save(out,'JPEG',quality=92,optimize=True)
    return f'https://ahorroscan.es/instagram-media/{out.name}'


def publish(r):
    me=api('GET','/me',{'fields':'id,user_id,username,name'}); ig=me['id']
    cap=caption(r)
    image_url=instagram_image_url(r)
    print(f'[INSTAGRAM] imagen preparada: {image_url}')
    c=api('POST',f'/{ig}/media',{'image_url':image_url,'caption':cap})
    cid=c['id']
    for _ in range(20):
        st=api('GET',f'/{cid}',{'fields':'id,status_code,status'})
        if st.get('status_code')=='FINISHED': break
        if st.get('status_code') in ('ERROR','EXPIRED'): raise RuntimeError(f'Container {st}')
        time.sleep(3)
    else: raise RuntimeError('Container timeout')
    # Instagram puede marcar el contenedor como FINISHED unos segundos antes de aceptar media_publish.
    # Reintentamos el publish ante el error transitorio 9007/2207027.
    last_error=None
    for attempt in range(6):
        try:
            pub=api('POST',f'/{ig}/media_publish',{'creation_id':cid})
            mid=pub['id']
            break
        except RuntimeError as e:
            last_error=e
            if 'Media ID is not available' not in str(e) or attempt == 5:
                raise
            time.sleep(5)
    else:
        raise last_error
    with db(IGDB) as c:
        c.execute('''INSERT OR REPLACE INTO instagram_publications(product_id,source,external_id,title,image_url,affiliate_url,price,discount_pct,score,media_id,status)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(r['product_id'],r['source'],r['external_id'],r['title'],r['image_url'],r['affiliate_url'],r['price'],r['discount'],r['score'],mid,'PUBLISHED'))
        c.commit()
    return mid,cap


def main():
    load_env(); init_db()
    if ARGS.publish and not publishing_enabled("instagram"):
        print(f"[INSTAGRAM] BLOQUEADA HA: {deny_reason('instagram')}")
        return 0
    if ARGS.publish:
        remaining=rate_limit_remaining()
        if remaining>0:
            print(f"[INSTAGRAM] PAUSA POR LIMITE META: quedan {remaining//3600} h {(remaining%3600)//60} min; no se hacen peticiones ni publicaciones")
            return 0
    if daily_count()>=MAX_PER_DAY: print('[INSTAGRAM] limite diario alcanzado'); return 0
    cand=candidates(); print(f'[INSTAGRAM] candidatos={len(cand)} limite_run={MAX_PER_RUN}')
    published=0
    for r in cand:
        if published >= MAX_PER_RUN:
            break
        print(f'[INSTAGRAM] {r["score"]:.2f} | {r["source"]} | {r["price"]:.2f}€ | {r["title"][:100]}')
        print(caption(r))
        if not ARGS.publish:
            continue
        try:
            mid,_=publish(r)
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            print(f'[INSTAGRAM] recurso de imagen no accesible, se prueba el siguiente candidato: {type(exc).__name__}: {exc}')
            continue
        except RuntimeError as exc:
            msg=str(exc)
            lower=msg.lower()
            if is_meta_rate_limit(msg):
                until=record_rate_limit(msg)
                print(f"[INSTAGRAM] LIMITE DE META ALCANZADO; pausa hasta {until.isoformat()}. No se reintenta en este ciclo.")
                return 0
            recoverable=(
                ('Instagram API HTTP 400:' in msg and (
                    'only photo or video can be accepted as media type' in lower
                    or 'invalid aspect ratio' in lower
                    or 'media type' in lower
                    or 'aspect ratio' in lower
                ))
                or 'container {' in lower
                or 'container timeout' in lower
                or 'media id is not available' in lower
                or 'candidate image invalid:' in lower
            )
            if not recoverable:
                raise
            print(f'[INSTAGRAM] error recuperable del candidato, se prueba el siguiente: {msg[:500]}')
            continue
        print(f'[INSTAGRAM] PUBLICADO media_id={mid}')
        published += 1
    return 0

import sys
ARGS=argparse.Namespace(publish=False) if False else None
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--publish',action='store_true'); ARGS=ap.parse_args(); raise SystemExit(main())
