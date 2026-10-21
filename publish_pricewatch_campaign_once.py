#!/usr/bin/env python3
"""One-time, deduplicated AhorroScan Price Watch campaign publisher."""
import json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
ENV=ROOT/'.env'
for line in ENV.read_text(encoding='utf-8').splitlines():
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1)
        os.environ.setdefault(k.strip(),v.strip().strip('"\''))
from telegram_api import send
TOKEN=os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN: raise SystemExit('Missing Telegram bot token')
PUBLISH='--publish' in sys.argv
STATE=ROOT/'data'/'marketing_campaign_pricewatch_20261016.json'
if STATE.exists():
    state=json.loads(STATE.read_text(encoding='utf-8'))
else:
    state={'campaign':'pricewatch_launch_oct2026','published':{},'created_at':datetime.now(timezone.utc).isoformat()}
if not isinstance(state.get('published'),dict): state['published']={}
channels=[('general','AHOROSCAN_TELEGRAM_CHAT_ID'),('tech','TELEGRAM_CHAT_ID'),('moviles','MOVILES_TELEGRAM_CHAT_ID'),('mascotas','MASCOTAS_TELEGRAM_CHAT_ID'),('moda','MODA_TELEGRAM_CHAT_ID'),('deportes','DEPORTE_TELEGRAM_CHAT_ID')]
photo='https://ahorroscan.es/assets/Buscador_AhorroScan.jpg'
results=[]
for name,key in channels:
    chat=os.getenv(key)
    if not chat:
        results.append({'channel':name,'status':'skipped_missing_chat'}); continue
    if chat in [os.getenv(k) for _,k in channels[:[n for n,_ in channels].index(name)]]:
        results.append({'channel':name,'status':'skipped_duplicate_chat'}); continue
    cycle=datetime.now(ZoneInfo('Europe/Madrid')).strftime('%Y-%m-%d')
    publication_key=f'{cycle}:{chat}'
    if publication_key in state['published']:
        results.append({'channel':name,'status':'already_published_today','message_id':state['published'][publication_key].get('message_id')}); continue
    landing=f'https://ahorroscan.es/?utm_source=telegram_{name}&utm_medium=telegram&utm_campaign=pricewatch_launch_oct2026#price-watch'
    guide=f'https://ahorroscan.es/guia-comprar-mejor/?utm_source=telegram_{name}&utm_medium=telegram&utm_campaign=pricewatch_launch_oct2026'
    caption=('🎯 TÚ ELIGES EL PRODUCTO. TÚ PONES EL PRECIO.\n\n'
      '¿Quieres comprar algo, pero no a cualquier precio? 🔎\n'
      'Busca el producto, decide cuánto quieres pagar y crea una alerta para no tener que revisar el precio cada día.\n\n'
      f'👇 Prueba el Buscador: {landing}\n'
      f'📘 Consejos para comprar mejor: {guide}\n\n'
      '#AhorroScan #PriceWatch #Ofertas #AhorroInteligente')
    if not PUBLISH:
        results.append({'channel':name,'status':'dry_run','text':caption}); continue
    try:
        response=send(TOKEN,'sendPhoto',{'chat_id':chat,'photo':photo,'caption':caption},timeout=30)
        msg=response['result']
        state['published'][publication_key]={'channel':name,'message_id':msg.get('message_id'),'published_at':datetime.now(timezone.utc).isoformat()}
        STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        results.append({'channel':name,'status':'published','message_id':msg.get('message_id')})
        time.sleep(1.5)
    except Exception as exc:
        results.append({'channel':name,'status':'error','reason':type(exc).__name__+': '+str(exc)[:180]})
        break
for r in results: print(json.dumps(r,ensure_ascii=False))
if PUBLISH:
    print('state_file='+str(STATE))
