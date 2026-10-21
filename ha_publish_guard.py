from __future__ import annotations
import json, os, time
from pathlib import Path
ROLE_FILE=Path(os.getenv("AHOROSCAN_ROLE_FILE",str(Path.home()/".config/ahorroscan/node-role.env")))
LEASE_STATE=Path(os.getenv("AHOROSCAN_LEASE_STATE",str(Path.home()/".config/ahorroscan/lease-state.json")))
def _values():
 v={}
 try:
  for line in ROLE_FILE.read_text(encoding="utf-8").splitlines():
   line=line.strip()
   if line and not line.startswith("#") and "=" in line: k,x=line.split("=",1); v[k.strip()]=x.strip()
 except FileNotFoundError: pass
 return v
def _lease_valid():
 try:
  s=json.loads(LEASE_STATE.read_text(encoding="utf-8")); return bool(s.get("granted")) and float(s.get("expires_at",0))>time.time()+5
 except (FileNotFoundError,ValueError,TypeError): return False
def _registered_channel(channel):
 try:
  from channel_registry import destinations
  return destinations().get(channel)
 except Exception:
  return None

def publishing_enabled(channel):
 v=_values(); config=_registered_channel(channel)
 if config and config.get("status")!="active": return False
 gate=(config or {}).get("publishing_enabled_env") or f"{channel.upper()}_PUBLISH_ENABLED"
 return v.get("NODE_ROLE")=="primary" and v.get("PUBLISH_ENABLED")=="1" and v.get(gate,"1")=="1" and _lease_valid()
def deny_reason(channel): return f"nodo no es PRIMARY, publicación {channel} desactivada o lease HA no válido ({ROLE_FILE}, {LEASE_STATE})"
