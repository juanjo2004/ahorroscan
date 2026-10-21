#!/usr/bin/env python3
"""Cliente mínimo para Awin Publisher API."""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE="https://api.awin.com"
TIMEOUT=45

class AwinError(RuntimeError):
    pass

def _cfg():
    token=os.getenv("AWIN_API_TOKEN","").strip()
    publisher=os.getenv("AWIN_PUBLISHER_ID","").strip()
    if not token or not publisher:
        raise AwinError("Faltan AWIN_API_TOKEN y/o AWIN_PUBLISHER_ID")
    return token,publisher

def _get(path, params):
    token,_=_cfg()
    r=requests.get(BASE+path, params=params,
                   headers={"Authorization":f"Bearer {token}"},
                   timeout=TIMEOUT)
    if not r.ok:
        raise AwinError(f"Awin HTTP {r.status_code}: {r.text[:500]}")
    return r.json()

def get_transactions(start=None,end=None,advertiser_id=None,region="ES"):
    _,publisher=_cfg()
    now=datetime.now(timezone.utc)
    end=end or now
    start=start or (end-timedelta(days=30))
    params={
        "startDate":start.isoformat().replace("+00:00","Z"),
        "endDate":end.isoformat().replace("+00:00","Z"),
        "dateType":"transaction",
        "region":region,
        "page":1,
        "pageSize":1000,
    }
    if advertiser_id:
        params["advertiserId"]=str(advertiser_id)
    return _get(f"/publishers/{publisher}/transactions/",params)

def get_advertiser_report(start=None,end=None,region="ES"):
    _,publisher=_cfg()
    now=datetime.now(timezone.utc)
    end=end or now
    start=start or (end-timedelta(days=30))
    params={
        "startDate":start.date().isoformat(),
        "endDate":end.date().isoformat(),
        "dateType":"transaction",
        "region":region,
    }
    return _get(f"/publishers/{publisher}/reports/advertiser",params)

if __name__=="__main__":
    from dotenv import load_dotenv
    load_dotenv(ROOT/".env")
    try:
        data=get_advertiser_report()
        print("[AWIN] conexión OK")
        print(data if isinstance(data,dict) else f"[AWIN] filas={len(data)}")
    except AwinError as e:
        print(f"[AWIN] no configurado: {e}")
