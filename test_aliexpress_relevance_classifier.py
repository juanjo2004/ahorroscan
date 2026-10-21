#!/usr/bin/env python3
import hashlib,hmac,json,re,time
from pathlib import Path
import requests
from config import ALI_APP_KEY,ALI_APP_SECRET,ALI_TRACKING_ID

ENDPOINT="https://api-sg.aliexpress.com/sync"
TOKEN_FILE=Path("data/aliexpress_token.json")
PARTNER_ID="iop44-sdk-typescript-20231021"
METHOD="aliexpress.affiliate.product.query"

RULES=[
("raton gaming",("perifericos","informatica y oficina","juegos y accesorios"),(("raton","ratón","mouse"),),("patines","skates","feet","pies","grip","cable","switch","microinterruptor","encoder","repuesto","replacement","estuche","funda","almohadilla","alfombrilla")),
("ssd nvme",("componentes de ordenadores","almacenamiento"),(("ssd","nvme","unidad de estado solido","unidad de estado sólido"),),("mini pc","laptop","notebook","carcasa","enclosure","adaptador","adapter","cable","conmutador","soporte","base")),
("memoria ram ddr5",("componentes de ordenadores",),(("memoria","ram"),("ddr5",)),("ddr4","ddr3","adaptador","adapter","plantilla","reballing","portatil","portátil","laptop","notebook")),
("monitor 4k",("monitores","pantallas"),(("monitor","pantalla","display"),("4k","uhd")),("camara","cámara","gafas","coche","dashcam","lente","lens")),
("teclado mecanico",("perifericos","periféricos","teclados"),(("teclado","keyboard"),("mecanico","mecánico","mechanical")),("soporte","stand","alfombrilla","mouse pad","pegatina","sticker","estuche","funda","mesa","organizador")),
]

def norm(s):
    s=(s or "").lower()
    return " ".join(s.replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").split())

def sign(params):
    c="".join(k+str(params[k]) for k in sorted(params) if params[k] not in (None,""))
    return hmac.new(str(ALI_APP_SECRET).encode(),c.encode(),hashlib.sha256).hexdigest().upper()

def fetch(q):
    tok=json.loads(TOKEN_FILE.read_text())["access_token"]
    p={"app_key":str(ALI_APP_KEY),"session":tok,"format":"json","method":METHOD,"partner_id":PARTNER_ID,"sign_method":"sha256","simplify":"false","timestamp":str(int(time.time()*1000)),"v":"2.0","keywords":q,"page_no":"1","page_size":"20","tracking_id":str(ALI_TRACKING_ID),"target_currency":"EUR","target_language":"ES","ship_to_country":"ES"}
    p["sign"]=sign(p)
    r=requests.post(ENDPOINT,data=p,timeout=30,headers={"Content-Type":"application/x-www-form-urlencoded;charset=utf-8"})
    r.raise_for_status()
    data=r.json()
    rr=data.get("aliexpress_affiliate_product_query_response",{}).get("resp_result",{})
    pro=rr.get("result",{}).get("products",{}).get("product",[])
    return pro if isinstance(pro,list) else []

def classify(p,cats,groups,forbidden):
    t=norm(str(p.get("product_title","")))
    cat=norm(f"{p.get('first_level_category_name','')} > {p.get('second_level_category_name','')}")
    reasons=[]
    if cats and not any(norm(c) in cat for c in cats): reasons.append("categoria")
    for g in groups:
        if not any(norm(x) in t for x in g): reasons.append("falta:"+"/".join(g))
    hits=[x for x in forbidden if norm(x) in t]
    if hits: reasons.append("prohibidas:"+",".join(hits))
    return not reasons,reasons

print("ALIEXPRESS - CLASIFICADOR DE RELEVANCIA")
print("No modifica SQLite, scanner ni Telegram.")
for q,cats,groups,forbidden in RULES:
    print(f"\n=== {q} ===")
    try: products=fetch(q)
    except Exception as e:
        print("ERROR:",type(e).__name__,e); continue
    okc=0
    for i,p in enumerate(products,1):
        ok,reasons=classify(p,cats,groups,forbidden); okc+=ok
        print(f"{i:02d}. [{'ACEPTAR' if ok else 'RECHAZAR'}] {p.get('product_title','<sin titulo>')}")
        print(f"    cat={p.get('first_level_category_name','n/d')} > {p.get('second_level_category_name','n/d')} | precio={p.get('target_sale_price') or p.get('sale_price') or p.get('app_sale_price','n/d')} | desc={p.get('discount','n/d')} | rating={p.get('evaluate_rate','n/d')} | ventas={p.get('lastest_volume','n/d')}")
        if reasons: print("    motivo="+"; ".join(reasons))
    print(f"Resumen: {okc}/{len(products)} aceptados = {(okc/len(products)*100 if products else 0):.1f}%")
