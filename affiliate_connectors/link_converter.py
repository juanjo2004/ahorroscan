"""Generador de enlaces de afiliación para URLs arbitrarias en redes admitidas."""
from __future__ import annotations
import os, json, time
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import requests

BOT_ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = BOT_ROOT / "data" / "aliexpress_token.json"
ALI_ENDPOINT = "https://api-sg.aliexpress.com/sync"
AWIN_DOMAINS = {"bricodepot.es": 69488, "www.bricodepot.es": 69488}

class LinkConversionError(ValueError): pass

def validate_url(raw):
    raw=(raw or "").strip()
    if not raw or len(raw)>2048: raise LinkConversionError("El enlace está vacío o es demasiado largo.")
    try:
        u=urlparse(raw)
        port=u.port
    except ValueError as exc:
        raise LinkConversionError("La URL no tiene un formato válido.") from exc
    if u.scheme not in ("http","https") or not u.hostname or u.username or u.password or port not in (None,80,443):
        raise LinkConversionError("Pega una URL http/https válida, sin credenciales incrustadas.")
    host=u.hostname.lower().rstrip(".")
    if host in {"localhost","localhost.localdomain"} or host.endswith((".local",".internal")) or host.replace('.','').isdigit():
        raise LinkConversionError("Este dominio no está permitido.")
    return u,host

def _amazon(u,host):
    tag=os.getenv("AMAZON_TAG", "").strip()
    if not tag: raise LinkConversionError("Amazon no está configurado: falta el ID de asociado.")
    if host not in {"amazon.es","www.amazon.es"}:
        raise LinkConversionError("Por ahora Amazon solo está habilitado para Amazon España (.es).")
    q=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k not in {"tag","ascsubtag","linkCode","linkId"}]
    q.append(("tag",tag))
    return urlunparse(("https",u.netloc,u.path,"",urlencode(q),""))

def _aliexpress(raw):
    # Reutiliza el signer y el OAuth token oficial ya usado por el conector del bot.
    import sys
    if str(BOT_ROOT) not in sys.path: sys.path.insert(0,str(BOT_ROOT))
    from sources.aliexpress import _sign, PARTNER_ID
    from config import ALI_APP_KEY, ALI_APP_SECRET, ALI_TRACKING_ID
    try: token=json.loads(TOKEN_FILE.read_text(encoding="utf-8")).get("access_token")
    except (OSError,ValueError): token=None
    if not all((ALI_APP_KEY,ALI_APP_SECRET,ALI_TRACKING_ID,token)):
        raise LinkConversionError("AliExpress no está listo: faltan credenciales o token OAuth.")
    params={"app_key":str(ALI_APP_KEY),"session":str(token),"format":"json","method":"aliexpress.affiliate.link.generate","partner_id":PARTNER_ID,"sign_method":"sha256","timestamp":str(int(time.time()*1000)),"v":"2.0","tracking_id":str(ALI_TRACKING_ID),"promotion_link_type":"0","source_values":raw}
    params["sign"]=_sign(params,str(ALI_APP_SECRET))
    try:
        r=requests.post(ALI_ENDPOINT,data=params,timeout=20,headers={"Content-Type":"application/x-www-form-urlencoded;charset=utf-8"})
        r.raise_for_status(); data=r.json()
    except requests.RequestException as e: raise LinkConversionError("AliExpress no respondió al generador oficial. Inténtalo más tarde.") from e
    node=data.get("aliexpress_affiliate_link_generate_response",{}).get("resp_result",{})
    if str(node.get("resp_code","200")) not in {"200","None"}: raise LinkConversionError("AliExpress rechazó la conversión para este enlace.")
    links=node.get("result",{}).get("promotion_links",{}).get("promotion_link",[])
    if isinstance(links,dict): links=[links]
    link=(links[0].get("promotion_link") if links else None)
    if not link: raise LinkConversionError("AliExpress no generó un enlace afiliado para este producto.")
    return link

def _awin(raw,host):
    try:
        from dotenv import load_dotenv
        load_dotenv("/app/hogar/.env", override=False)
    except ImportError:
        pass
    advertiser=AWIN_DOMAINS.get(host)
    if not advertiser: raise LinkConversionError("Esta tienda no tiene un programa Awin activo y autorizado para conversión automática en AhorroScan.")
    # Use existing official Awin link builder; no attempt to bypass advertiser approval.
    import sys
    hogar=Path("/app/hogar")
    if hogar.exists() and str(hogar) not in sys.path: sys.path.insert(0,str(hogar))
    try:
        from sources.awin_linkbuilder import generate_tracking_link
        link=generate_tracking_link(advertiser,raw,clickref="ahorroscan_link_converter")
    except Exception as e:
        raise LinkConversionError("Awin no pudo crear el deeplink. Comprueba que el anunciante permite deeplinks y que el token tiene acceso.") from e
    return link

def convert_url(raw):
    u,host=validate_url(raw)
    if host in {"amazon.es","www.amazon.es"}: return {"store":"Amazon España","affiliate_url":_amazon(u,host),"method":"amazon_associate_tag"}
    if host=="aliexpress.com" or host.endswith(".aliexpress.com"): return {"store":"AliExpress","affiliate_url":_aliexpress(raw),"method":"aliexpress_official_api"}
    if host in AWIN_DOMAINS: return {"store":"Brico Depôt (Awin)","affiliate_url":_awin(raw,host),"method":"awin_link_builder"}
    raise LinkConversionError("Tienda no compatible todavía. Actualmente se admiten Amazon España, AliExpress y Brico Depôt vía Awin, sujetos a la autorización de cada programa.")
