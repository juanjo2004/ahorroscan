#!/usr/bin/env python3
"""Sincroniza redes con el ledger de monetización.

Awin: API directa cuando existen credenciales.
Amazon/AliExpress: importación segura desde archivos exportados en inbox.
"""
from __future__ import annotations
import csv, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent
INBOX=ROOT/"data"/"affiliate_reports"/"inbox"
HOGAR_ENV=Path("/home/debian/ahorroscan/test/current/ahorroscan-hogar/.env")
if HOGAR_ENV.exists():
    load_dotenv(HOGAR_ENV, override=False)
load_dotenv(ROOT/".env", override=False)

def awin_sync():
    from affiliate_connectors.awin import get_transactions
    end=datetime.now(timezone.utc)
    start=end-timedelta(days=30)
    raw=get_transactions(start=start,end=end,region="ES")
    rows=raw.get("data",raw) if isinstance(raw,dict) else raw
    if not isinstance(rows,list): rows=[]
    out=INBOX/"awin_api_latest.csv"
    fields=["network","merchant","transaction_id","order_date","amount","commission","currency","status","product_id","project","season"]
    with out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for x in rows:
            if not isinstance(x,dict): continue
            w.writerow({
                "network":"awin",
                "merchant":x.get("advertiserName") or x.get("advertiser_name") or x.get("programName") or "",
                "transaction_id":x.get("id") or x.get("transactionId") or x.get("transaction_id") or x.get("orderRef") or "",
                "order_date":x.get("transactionDate") or x.get("transaction_date") or x.get("date") or "",
                "amount":x.get("saleAmount") or x.get("sale_amount") or x.get("amount") or 0,
                "commission":x.get("commissionAmount") or x.get("commission") or 0,
                "currency":x.get("currency") or "EUR",
                "status":x.get("status") or "reported",
                "product_id":x.get("productId") or "",
                "project":x.get("clickRef") or "",
                "season":"",
            })
    print(f"[AFFILIATE] Awin filas recibidas={len(rows)} -> {out.name}")

def main():
    INBOX.mkdir(parents=True,exist_ok=True)
    if os.getenv("AWIN_API_TOKEN","").strip() and os.getenv("AWIN_PUBLISHER_ID","").strip():
        try: awin_sync()
        except Exception as e:
            print(f"[AFFILIATE] Awin error: {e}",file=sys.stderr)
            return 2
    else:
        print("[AFFILIATE] Awin omitido: credenciales no configuradas")
    import monetization_engine
    monetization_engine.init()
    n=monetization_engine.import_csvs()
    monetization_engine.build()
    print(f"[AFFILIATE] importadas={n}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
