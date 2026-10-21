#!/usr/bin/env python3
from __future__ import annotations
import json, os, sqlite3, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "ofertas.db"
ROLE_FILE = Path.home()/".config/ahorroscan/node-role.env"
LEASE_STATE = Path.home()/".config/ahorroscan/lease-state.json"
ENV_FILE = Path.home()/".config/ahorroscan/watchdog.env"
STATE_FILE = Path.home()/".config/ahorroscan/channel-freshness.state.json"

CHANNELS = {
    "Tech": ("publications", 6),
    "Móviles": ("mobile_publications", 30),
    "Mascotas": ("pet_publications", 30),
    "Moda": ("fashion_publications", 30),
    "Deportes": ("sports_publications", 30),
}
WARN_IF_NO_CANDIDATE_HOURS = 24

def load_env(path):
    out={}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k,v=line.split("=",1); out[k.strip()]=v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out

def primary_and_lease_valid():
    role=load_env(ROLE_FILE)
    if role.get("NODE_ROLE") != "primary" or role.get("PUBLISH_ENABLED") != "1":
        return False
    try:
        state=json.loads(LEASE_STATE.read_text())
        return bool(state.get("granted")) and float(state.get("expires_at",0)) > time.time()+5
    except Exception:
        return False

def query_latest(conn, table):
    try:
        row=conn.execute(f"SELECT published_at FROM {table} ORDER BY published_at DESC, id DESC LIMIT 1").fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None

def hours_since(value):
    if not value: return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return max(0,(datetime.now(timezone.utc)-dt).total_seconds()/3600)
    except Exception:
        return None

def send_alert(message):
    env=load_env(ENV_FILE)
    token=env.get("AHOROSCAN_ALERT_BOT_TOKEN")
    chat=env.get("AHOROSCAN_ALERT_CHAT_ID")
    if not token or not chat: return False
    data=urllib.parse.urlencode({"chat_id":chat,"text":message}).encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",data=data,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=10) as r:
            return 200 <= r.status < 300
    except Exception:
        return False

def main():
    # Sólo alerta el nodo que realmente tiene capacidad de publicar.
    if not primary_and_lease_valid():
        return 0
    conn=sqlite3.connect(DB_PATH)
    alerts=[]
    snapshot={}
    for name,(table,limit) in CHANNELS.items():
        latest=query_latest(conn,table)
        age=hours_since(latest)
        snapshot[name]={"latest":latest,"age_hours":round(age,1) if age is not None else None}
        if age is None:
            alerts.append(f"🔴 {name}: sin publicaciones registradas")
        elif age > limit:
            alerts.append(f"🟠 {name}: {age:.1f} h sin publicar (límite {limit} h)")
    conn.close()

    previous={}
    try: previous=json.loads(STATE_FILE.read_text())
    except Exception: pass

    # Una alerta al entrar en estado degradado y otra cuando se recupera.
    current_key="|".join(alerts)
    previous_key=previous.get("alert_key","")
    if alerts and current_key != previous_key:
        send_alert("🚨 AhorroScan · SALUD DE CANALES\n\n"+"\n".join(alerts))
    elif not alerts and previous_key:
        send_alert("✅ AhorroScan · CANALES RECUPERADOS\n\nTodos los canales monitorizados tienen actividad reciente.")

    STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    STATE_FILE.write_text(json.dumps({"alert_key":current_key,"snapshot":snapshot},ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
