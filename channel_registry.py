"""Registro central de familias y canales de AhorroScan.

La infraestructura puede crecer a nuevos canales sin duplicar el pipeline.
Los canales en estado 'planned' nunca publican por accidente.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"


def _load(name):
    with (CONFIG / name).open(encoding="utf-8") as f:
        return json.load(f)


def families():
    return _load("families.json")["families"]


def channels():
    return _load("channels.json")["channels"]


def destinations():
    """Return Telegram channels and auxiliary publishers from one registry."""
    data = _load("channels.json")
    result = dict(data.get("channels", {}))
    result.update(data.get("destinations", {}))
    return result


def active_destinations():
    return {
        name: config
        for name, config in destinations().items()
        if config.get("status") == "active"
    }


def get_channel(channel_id: str):
    return channels().get(channel_id)


def get_family(family_id: str):
    return families().get(family_id)


def is_active(channel_id: str) -> bool:
    c = get_channel(channel_id)
    return bool(c and c.get("status") == "active")


def categories_for_channel(channel_id: str) -> list[str]:
    c = get_channel(channel_id)
    if not c:
        return []
    return list((get_family(c.get("family")) or {}).get("categories", []))


def planned_channels() -> list[str]:
    return [k for k, v in channels().items() if v.get("status") == "planned"]
