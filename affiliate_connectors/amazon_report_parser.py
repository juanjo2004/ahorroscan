#!/usr/bin/env python3
"""Normaliza informes tabulados de Amazon Associates ES al formato AhorroScan."""
from __future__ import annotations
import csv
from pathlib import Path

def _norm(s):
    return " ".join(str(s or "").strip().lower().replace("\ufeff","").split())

def parse(path):
    path=Path(path)
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        sample=f.read(4096); f.seek(0)
        dialect=csv.Sniffer().sniff(sample,delimiters="\t,;")
        rows=csv.DictReader(f,dialect=dialect)
        out=[]
        for row in rows:
            n={_norm(k):v for k,v in row.items()}
            tx=n.get("order id") or n.get("order_id") or n.get("transaction id") or n.get("id")
            if not tx:
                continue
            def pick(*keys):
                for k in keys:
                    if k in n and n[k] not in ("",None):
                        return n[k]
                return ""
            out.append({
                "network":"amazon",
                "merchant":"Amazon.es",
                "transaction_id":tx,
                "order_date":pick("order date","date","order date/time"),
                "amount":pick("revenue","sale amount","order value","amount"),
                "commission":pick("earnings","referral commission earnings","commission"),
                "currency":"EUR",
                "status":pick("status","order status") or "reported",
                "product_id":pick("product_id","product id"),
                "project":pick("project","tracking id","tracking_id") or None,
            })
    return out
