#!/usr/bin/env python3
from __future__ import annotations
import json, os, time
from pathlib import Path
from urllib.request import Request, urlopen
NODE=os.getenv("AHOROSCAN_NODE_NAME","raspi4"); RANK=int(os.getenv("AHOROSCAN_NODE_RANK","2")); URL=os.getenv("AHOROSCAN_LEASE_URL","").rstrip("/"); SECRET=os.getenv("AHOROSCAN_LEASE_SECRET","")
STATE=Path(os.getenv("AHOROSCAN_LEASE_STATE",str(Path.home()/".config/ahorroscan/lease-state.json"))); ROLE=Path(os.getenv("AHOROSCAN_ROLE_FILE",str(Path.home()/".config/ahorroscan/node-role.env"))); TTL=60
def call(path):
 req=Request(URL+path,data=json.dumps({"node":NODE,"rank":RANK,"ttl":TTL}).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer "+SECRET,"User-Agent":"AhorroScan-Lease-Agent/1.0"},method="POST")
 with urlopen(req,timeout=8) as r:return json.loads(r.read())
def write_role(primary):
 ROLE.parent.mkdir(parents=True,exist_ok=True); ROLE.write_text("# AhorroScan HA node role\nNODE_ROLE=%s\nPUBLISH_ENABLED=%d\nTELEGRAM_PUBLISH_ENABLED=%d\nINSTAGRAM_PUBLISH_ENABLED=%d\n"%("primary" if primary else "standby",1 if primary else 0,1 if primary else 0,1 if primary else 0),encoding="utf-8")
def main():
 if not URL or not SECRET: raise SystemExit("lease not configured")
 STATE.parent.mkdir(parents=True,exist_ok=True)
 while True:
  try:
   data=call("/acquire"); granted=bool(data.get("granted")); STATE.write_text(json.dumps({"node":NODE,"rank":RANK,"granted":granted,"token":data.get("token"),"expires_at":data.get("expiresAt",0)/1000,"checked_at":time.time()},indent=2),encoding="utf-8"); write_role(granted); time.sleep(15 if granted else min(15,max(5,data.get("retryAfterMs",15000)/1000)))
  except Exception as e:
   STATE.write_text(json.dumps({"node":NODE,"rank":RANK,"granted":False,"token":None,"expires_at":0,"checked_at":time.time(),"error":str(e)}),encoding="utf-8"); write_role(False); time.sleep(15)
if __name__=="__main__": main()
