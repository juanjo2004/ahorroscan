#!/usr/bin/env python3
from __future__ import annotations
import hashlib,hmac,json,re,time
from pathlib import Path
import requests
from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID

ENDPOINT="https://api-sg.aliexpress.com/sync"
TOKEN_FILE=Path("data/aliexpress_token.json")
METHOD="aliexpress.affiliate.product.query"
PARTNER_ID="iop44-sdk-typescript-20231021"

QUERIES={
    "raton gaming":[
        "raton gaming",
        "gaming mouse",
        "raton gaming inalambrico",
        "wireless gaming mouse",
        "mouse optico gaming",
    ],
    "ssd nvme":[
        "ssd nvme",
        "ssd nvme 1tb m2",
        "m2 nvme ssd 1tb",
        "pcie 4.0 nvme ssd",
        "2280 nvme ssd",
    ],
    "monitor 4k":[
        "monitor 4k",
        "monitor 4k 27 pulgadas",
        "4k gaming monitor",
        "uhd monitor 27",
        "ips 4k monitor",
    ],
    "teclado mecanico":[
        "teclado mecanico",
        "mechanical keyboard",
        "teclado gaming mecanico",
        "87 key mechanical keyboard",
        "75 percent mechanical keyboard",
    ],
}

def norm(s):
    table=str.maketrans({"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"})
    return " ".join((s or "").lower().translate(table).split())

def sign(p):
    c="".join(k+str(p[k]) for k in sorted(p) if p[k] not in (None,""))
    return hmac.new(str(ALI_APP_SECRET).encode(),c.encode(),hashlib.sha256).hexdigest().upper()

def fetch(q):
    token=json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    if not token: raise RuntimeError("Falta access_token")
    p={
        "app_key":str(ALI_APP_KEY),"session":token,"format":"json",
        "method":METHOD,"partner_id":PARTNER_ID,"sign_method":"sha256",
        "simplify":"false","timestamp":str(int(time.time()*1000)),
        "v":"2.0","keywords":q,"page_no":"1","page_size":"20",
        "tracking_id":str(ALI_TRACKING_ID),"target_currency":"EUR",
        "target_language":"ES","ship_to_country":"ES",
    }
    p["sign"]=sign(p)
    r=requests.post(ENDPOINT,data=p,timeout=30,
                    headers={"Content-Type":"application/x-www-form-urlencoded;charset=utf-8"})
    r.raise_for_status()
    data=r.json()
    rr=data.get("aliexpress_affiliate_product_query_response",{}).get("resp_result",{})
    result=rr.get("result",{}) if isinstance(rr,dict) else {}
    products=result.get("products",{}).get("product",[]) if isinstance(result,dict) else []
    return products if isinstance(products,list) else []

def title_score(title,cat):
    t=norm(title); c=norm(cat)
    # Lightweight relevance meter only for comparing query variants.
    s=0
    if any(x in t for x in ("raton","mouse")): s+=20
    if "gaming" in t or "gamer" in t: s+=15
    if any(x in t for x in ("ssd","nvme")): s+=20
    if "m.2" in t: s+=15
    if "1tb" in t or "2tb" in t or "500gb" in t: s+=10
    if "monitor" in t or "pantalla" in t or "display" in t: s+=20
    if "4k" in t or "uhd" in t: s+=15
    if "teclado" in t or "keyboard" in t: s+=20
    if "mecanico" in t or "mechanical" in t: s+=15
    if any(x in c for x in ("perifericos","componentes de ordenadores","monitores")): s+=10
    negatives=("patines","carcasa","enclosure","mini pc","adaptador","disipador","alfombrilla",
               "camara","cámara","gafas","proyector","soporte","juguete","pegatina","repuesto")
    s-=min(60,20*sum(1 for x in negatives if x in t))
    return max(0,min(100,s))

def main():
    print("ALIEXPRESS - QUERY DIVERSIFICATION V1")
    print("Compara variantes de búsqueda. No modifica SQLite, scanner ni Telegram.\n")
    for category, queries in QUERIES.items():
        print(f"===== {category} =====")
        for q in queries:
            try: products=fetch(q)
            except Exception as e:
                print(f"\nQUERY: {q}\nERROR: {type(e).__name__}: {e}")
                continue
            ranked=[]
            for p in products:
                t=p.get("product_title","")
                cat=f"{p.get('first_level_category_name','')} > {p.get('second_level_category_name','')}"
                ranked.append((title_score(t,cat),p,cat))
            ranked.sort(reverse=True,key=lambda x:x[0])
            print(f"\nQUERY: {q} | resultados={len(ranked)}")
            for i,(s,p,cat) in enumerate(ranked[:8],1):
                print(f"{i:02d}. [{s:3d}] {p.get('product_title','<sin titulo>')}")
                print(f"    precio={p.get('target_sale_price') or p.get('sale_price') or p.get('app_sale_price') or 'n/d'} | desc={p.get('discount','n/d')} | rating={p.get('evaluate_rate','n/d')} | ventas={p.get('lastest_volume','n/d')}")
                print(f"    cat={cat}")
            print(f"TOP8_M>=70: {sum(1 for s,_,_ in ranked[:8] if s>=70)}")
    print("\nFIN. Buscamos consultas que generen producto principal real, no solo coincidencias de texto.")

if __name__=="__main__":
    main()
